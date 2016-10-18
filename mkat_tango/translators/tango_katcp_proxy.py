#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
    @author MeerKAT CAM team <cam@ska.ac.za>
"""
import sys
import weakref
import logging
import os

import tornado
import PyTango

from concurrent.futures import Future
from katcp import inspecting_client, ioloop_manager, Message
from katcp.core import Sensor
from katcp.client import BlockingClient

from mkat_tango import helper_module
from mkat_tango.translators.utilities import katcpname2tangoname

from PyTango import DevDouble, DevLong64, DevBoolean, DevString, DevFailed, DevState
from PyTango import Attr, UserDefaultAttrProp, AttrWriteType, AttrQuality, Database
from PyTango.server import Device, DeviceMeta, command, attribute
from PyTango.server import server_run, device_property

MODULE_LOGGER = logging.getLogger(__name__)

KATCP_TYPE_TO_TANGO_TYPE = {
    'integer': DevLong64,
    'float': DevDouble,
    'boolean': DevBoolean,
    'lru': DevString,
    'discrete': DevString,  # TODO (KM) 2016-06-10 : Need to change to DevEnum
                            # once solution is found
    'string': DevString,
    'timestamp': DevDouble,
    'address': DevString
    }

KATCP_SENSOR_STATUS_TO_TANGO_ATTRIBUTE_QUALITY = {
        Sensor.NOMINAL: AttrQuality.ATTR_VALID,
        Sensor.WARN: AttrQuality.ATTR_WARNING,
        Sensor.ERROR: AttrQuality.ATTR_ALARM,
        Sensor.FAILURE: AttrQuality.ATTR_INVALID,
        Sensor.UNKNOWN: AttrQuality.ATTR_INVALID,
        Sensor.INACTIVE: AttrQuality.ATTR_INVALID  # TODO (AR) 2016-06-10: We should
        #  probably rather remove the TANGO attribute if the KATCP sensor is 'inactive'.
        }

def kattype2tangotype_object(katcp_sens_type):
    """Convert KATCP Sensor type to A corresponding TANGO type object

    Parameters
    ----------
    katcp_sens_type: str
        Representing the KATCP sensor object type.

    Returns
    -------
    tango_type: PyTango.CmdArgType enum

    """
    try:
        tango_type = KATCP_TYPE_TO_TANGO_TYPE[katcp_sens_type]
    except KeyError as ke:
        raise NotImplementedError("Sensor type {} not yet implemented or is invalid"
                                  .format(tango_type))
    return tango_type

def katcp_sensor2tango_attr(sensor):
    """Convert KATCP type object to corresponding TANGO type object

    Parameters
    ----------
    sensor: A katcp.Sensor object

    Returns
    -------
    attribute: A PyTango.Attr object

    """
    tango_type = kattype2tangotype_object(sensor.stype)
    attr_props = UserDefaultAttrProp()  # Used to set the attribute default properties
    attr_name = katcpname2tangoname(sensor.name)
    attribute = Attr(attr_name, tango_type, AttrWriteType.READ)
    if sensor.stype in ['integer', 'float']:
        if sensor.params:
            attr_props.set_min_value(str(sensor.params[0]))
            attr_props.set_max_value(str(sensor.params[1]))

    attr_props.set_label(sensor.name)
    attr_props.set_description(sensor.description)
    if sensor.units:
        # Seems to cause a seg fault if units is empty
        attr_props.set_unit(sensor.units)
    attribute.set_default_properties(attr_props)
    return attribute

def add_tango_server_attribute_list(tango_dserver, sensors, error_list=None):
    """Add in new TANGO attributes.

    Parameters
    ----------
    tango_dserver: A PyTango.TangoDeviceServer instance
        Tango Attributes mirroring the KATCP sensors in sensor_list are added to
        tango_dserver.
    sensors: dict()
        A dictionary mapping sensor names to katcp.Sensor objects.
    error_list : list or None
        List of sensors that could not be translated due to an error
        condition. Will append error-sensors to this list.

    Returns
    -------
    None

    """
    # Sort by sensor names so that the don't show up in the tango system in a
    # random order.
    for _, sensor in sorted(sensors.items()):
        try:
            attribute = katcp_sensor2tango_attr(sensor)
            tango_dserver.add_attribute(attribute, tango_dserver.read_attr)
        except Exception:
            MODULE_LOGGER.exception(
                'Exception trying to add sensor {} to tango server'
                .format(sensor.name))
            if error_list is not None:
                error_list.append(sensor.name)

def remove_tango_server_attribute_list(tango_dserver, sensors, error_list=None):
    """Remove existing TANGO attributes.

    Parameters
    ----------
    tango_dserver: A PyTango.TangoDeviceServer instance
        Tango Attributes mirroring the KATCP sensors in sensor_list are added to
        tango_dserver.
    sensors: dict()
        A dictionary mapping sensor names to katcp.Sensor objects
    error_list : list or None
        List of sensors that could not be translated due to an error
        condition. Will remove error-sensors to this list if they are removed
        from the KATCP device

    Returns
    -------
    None

    """
    for sensor_name in sensors.keys():
        attr_name = katcpname2tangoname(sensor_name)
        if error_list is not None:
            try:
                error_list.remove(sensor_name)
            except ValueError:
                # OK if this was not an error-sensor.
                pass
        try:
            tango_dserver.remove_attribute(attr_name)
        except DevFailed:
            MODULE_LOGGER.debug("Attribute {} does not exist".format(attr_name))

def create_command2request_handler(req_name, req_doc):
    """Convert katcp request decription into a tango command handler

    Parameters
    ----------
    req_name : str
        Name of the katcp request
    req_doc : str
        Request doc string

    Returns
    -------
    command : PyTango.server.command obj
        Tango device server command
    """
    if 'Parameters' in req_doc:
        def cmd_handler(self, request_args):
            MODULE_LOGGER.info("Executing request {}".format(req_name))
            reply = self.tango_katcp_proxy.do_request(
                    req_name, request_args)
            MODULE_LOGGER.info(reply.arguments)
            return reply.arguments
        cmd_handler.__name__ = katcpname2tangoname(req_name)
        return command(f=cmd_handler, dtype_in=(str,),
                       dtype_out=(str,), doc_in=req_doc)
    else:
        def cmd_handler(self):
            MODULE_LOGGER.info("Executing request {}".format(req_name))
            reply = self.tango_katcp_proxy.do_request(req_name)
            MODULE_LOGGER.info(reply.arguments)
            return reply.arguments
        cmd_handler.__name__ = katcpname2tangoname(req_name)
        return command(f=cmd_handler, doc_in='No input parameters',
                       dtype_out=(str,), doc_out=req_doc)

class TangoDeviceServerBase(Device):
    instances = weakref.WeakValueDictionary()

    katcp_address = device_property(
        dtype=str, doc=
        'katcp address of the device to translate as <host>:<port>')
    katcp_sync_timeout = device_property(
        dtype=float, default_value=5, doc=
        'Timeout (in seconds) for syncing with the KATCP device at startup')

    def __init__(self, *args, **kwargs):
        self.tango_katcp_proxy = None
        self._first_inspection_done = False
        Device.__init__(self, *args, **kwargs)

    @attribute(dtype=(str,), doc="List of KATCP sensors that could not be "
               "translated due to an unexpected error",
               max_dim_x=10000, polling_period=10000)
    def ErrorTranslatingSensors(self):
        # TODO NM 2016-08-30 Perhaps change it into a table that also contains
        # the reason for non-translation?
        return self.tango_katcp_proxy.untranslated_sensors

    @attribute(dtype=int, doc='Number or sensors that were not translated due '
               'to an unexpected error', max_alarm=1, polling_period=10000)
    def NumErrorTranslatingSensors(self):
        return len(self.tango_katcp_proxy.untranslated_sensors)

    @attribute(dtype=(str,), doc="List of KATCP request replies",
               max_dim_x=10000, max_dim_y=1000, polling_period=1000)
    def Replies(self):
        return self.tango_katcp_proxy.replies

    @attribute(dtype=(str,), doc="List of KATCP request informs",
               max_dim_x=10000, max_dim_y=1000, polling_period=1000)
    def Informs(self):
        return self.tango_katcp_proxy.informs

    def init_device(self):
        if self.tango_katcp_proxy:
            self.tango_katcp_proxy.ioloop.add_callback(
                    self.tango_katcp_proxy.ioloop.stop)

        Device.init_device(self)
        self.set_state(DevState.ON)
        name = self.get_name()
        self.instances[name] = self
        katcp_host, katcp_port = self.katcp_address.split(':')
        katcp_port = int(katcp_port)
        self.tango_katcp_proxy = (
                KatcpTango2DeviceProxy.from_katcp_address_tango_device(
                    (katcp_host, katcp_port), self))
        self.tango_katcp_proxy.start()
        # The conditional statement resolves the tango server error:
        # Not able to acquire serialization (dev, class or process) monitor.
        # Reason being API command timeout i.e. ~3000 mS exceeded.
        # It happens during testing when the device test class sets up the
        # testing environment by executing the device init command on the
        # server side meanwhile the KatcpTango2DeviceProxy executes the command
        # so we get a timeout error, this prevents frequent syncing of
        # inspecting client to the katcp server thus a single inspection is ok.
        # Note that one monitor per device which is taken when the command
        # starts and which is released when the command ends.
        if not self._first_inspection_done:
            MODULE_LOGGER.info('Waiting {}s for katcp sync'.format(
                self.katcp_sync_timeout))
            self.tango_katcp_proxy.wait_synced(self.katcp_sync_timeout)
            MODULE_LOGGER.info('katcp synced')
            self._first_inspection_done = True

    def read_attr(self, attr):
        '''Read value for an attribute from the katcp sensor observer updates
        into the Tango attribute

        Parameters
        ----------
        attribute : PyTango.Attribute
            The attribute into which the value is read from the katcp sensor observer.

        Note: `attr` is modified in place.

        '''
        name = attr.get_name()
        sensor_updates = self.tango_katcp_proxy.sensor_observer.updates[name]
        quality = KATCP_SENSOR_STATUS_TO_TANGO_ATTRIBUTE_QUALITY[
                sensor_updates['status']]
        timestamp = sensor_updates['timestamp']
        value = sensor_updates['value']
        self.info_stream("Reading attribute {} : {}".format(name, sensor_updates))
        attr.set_value_date_quality(value, timestamp, quality)

class KatcpTango2DeviceProxy(object):
    def __init__(self, katcp_inspecting_client, tango_device_server, ioloop):
        self.katcp_inspecting_client = katcp_inspecting_client
        self.tango_device_server = tango_device_server
        self.ioloop = ioloop
        self.sensor_observer = SensorObserver()
        self.untranslated_sensors = []
        self.replies = []
        self.informs = []

    def start(self):
        """Start the translator

        Starts the KATCP inspecting client

        """
        self.katcp_inspecting_client.set_state_callback(self.katcp_state_callback)
        self.ioloop.add_callback(self.katcp_inspecting_client.connect)

    def stop(self, timeout=1.0):
        """Stop the ioloop and thus the KATCP inspecting client

        """
        self.ioloop.add_callback(self.ioloop.stop)

    def wait_synced(self, timeout=None):
        f = Future()            # Should be a thread-safe future
        if timeout is None:
            timeout = self.katcp_sync_timeout

        @tornado.gen.coroutine
        def _wait_synced():
            try:
                yield self.katcp_inspecting_client.until_synced(timeout)
            except Exception as exc:
                f.set_exception(exc)
            else:
                f.set_result(None)
        self.ioloop.add_callback(_wait_synced)
        f.result(timeout=timeout)

    def do_request(self, req, request_args=None, katcp_request_timeout=5.0):
        """Execute a KATCP request using a command handler.

        Parameters
        ----------
        req : str
            request name
        request_args : list
            request parameters in string format
        katcp_request_timeout : float
            KATCP request timeout

        Returns
        -------
        reply : katcp.Message
            katcp request reply

        """
        f = Future()            # Should be a thread-safe future
        if request_args is None:
            request_args = []

        @tornado.gen.coroutine
        def _wait_synced():
            try:
                reply, informs = yield self.katcp_inspecting_client.simple_request(
                                                req, *request_args)
            except Exception as exc:
                f.set_exception(exc)
            else:
                f.set_result([reply, informs])
        self.ioloop.add_callback(_wait_synced)
        reply, informs = f.result(timeout=katcp_request_timeout)
        self.replies = reply.arguments
        self.informs = []
        for inf in informs:
            self.informs.extend(inf.arguments)
        return reply

    @tornado.gen.coroutine
    def katcp_state_callback(self, state, model_changes):
        if model_changes:
            sensor_changes = model_changes.get('sensors', {})
            added_sensors = sensor_changes.get('added', set())
            removed_sensors = sensor_changes.get('removed', set())
            yield self.reconfigure_tango_device_server(removed_sensors, added_sensors)

    @tornado.gen.coroutine
    def reconfigure_tango_device_server(self, removed_sens, added_sens):
        removed_sensors = dict()
        for sens_name in removed_sens:
            sensor = yield self.katcp_inspecting_client.future_get_sensor(sens_name)
            removed_sensors[sens_name] = sensor
        remove_tango_server_attribute_list(
            self.tango_device_server, removed_sensors, self.untranslated_sensors)

        added_sensors = dict()
        for sens_name in added_sens:
            sensor = yield self.katcp_inspecting_client.future_get_sensor(sens_name)
            sensor.attach(self.sensor_observer)
            added_sensors[sens_name] = sensor
        add_tango_server_attribute_list(
            self.tango_device_server, added_sensors, self.untranslated_sensors)
        self._setup_sensor_sampling()

    @tornado.gen.coroutine
    def _setup_sensor_sampling(self):
        for sensor_name in self.katcp_inspecting_client.sensors:
            reply, informs = yield self.katcp_inspecting_client.simple_request(
                    'sensor-sampling', sensor_name, 'event')
            if not reply.reply_ok():
                MODULE_LOGGER.debug("Unexpected failure reply for {} sensor. \n" +
                        " Informs: {} \n Reply: {}".format(sensor_name, informs, reply))

    @classmethod
    def from_katcp_address_tango_device(cls,
            katcp_server_address, tango_device_server):
        """Instatiate KatcpTango2DeviceProxy from network address

        Parameters
        ----------
        katcp_server_address : tuple (hostname : str, port : int)
            Address where the KATCP server interface is listening
        tango_device_server : PyTango.Device
            Tango device that has the results of the translated katcp proxy

        """
        katcp_host, katcp_port = katcp_server_address
        iolm = ioloop_manager.IOLoopManager()
        iolm.setDaemon(True)
        ioloop = iolm.get_ioloop()
        iolm.start()
        katcp_inspecting_client = inspecting_client.InspectingClientAsync(
            katcp_host, katcp_port, ioloop=ioloop)
        return cls(katcp_inspecting_client, tango_device_server, ioloop)

class SensorObserver(object):
    """The observer class attached to KATCP sensor to recieve updates after the
    sensor strategy is set."""
    def __init__(self):
        self.updates = dict()

    def update(self, sensor, reading):
        read_dict = {'timestamp': reading.timestamp,
                'status': reading.status, 'value': reading.value}
        if sensor.stype in ['address']:
            # Address sensor type contains a Tuple contaning (host, port) and
            # mapped to tango DevString type i.e "host:port"
            read_dict['value'] = ':'.join(str(s) for s in reading.value)
        self.updates[katcpname2tangoname(sensor.name)] = read_dict
        MODULE_LOGGER.debug('Received {!r} for attr {!r}'.format(sensor, reading))

def get_katcp_address(server_name):
    """Gets the KATCP address of a running KATCP device form the tango-db device
    properties

    Parameters
    ----------
    server_name : str
        Tango device server name in tango format
        e.g. 'tango_katcp_proxy/test'


    Returns
    -------
    katcp_address : str
        Address of a running KATCP device
        e.g. 'localhost:50000'

    """
    db = Database()
    server_class = db.get_server_class_list(server_name).value_string[0]
    device_name = db.get_device_name(server_name, server_class).value_string[0]
    katcp_address = db.get_device_property(device_name,
            'katcp_address')['katcp_address'][0]
    return katcp_address

def get_katcp_request_data(katcp_connect_timeout=60.0):
    """Inspects the KATCP device for requests using a temporary BlockingClient.

    Parameters
    ----------
    katcp_connect_timeout: float
        Client connection timeout to a KATCP device


    Returns
    -------
    req_dict : dict
        Dictionary of requests with request descriptions where
        are keys = request_name and values = request_documentation

    """
    server_name = helper_module.get_server_name()
    katcp_address = get_katcp_address(server_name)
    katcp_host, katcp_port = katcp_address.split(':')
    katcp_port = int(katcp_port)
    client = BlockingClient(katcp_host, katcp_port)
    try:
        client.start()
        client.wait_connected(timeout=katcp_connect_timeout)
        help_m = Message.request('help')
        reply, informs = client.blocking_request(help_m)
    finally:
        client.stop()
        client.join()
    req_list = [req.arguments for req in informs]
    req_dict = dict()
    for req in req_list:
        req_dict[req[0]] = req[1]
    return req_dict

def get_tango_device_server():
    """Declares a tango device class that inherits the Device class and then
    adds tango commands.

    Returns
    -------
    TangoDeviceServer : PyTango.Device
        Tango device that has the results of the translated KATCP server

    """
    requests_dict = get_katcp_request_data()

    # Declare a Tango Device class for specifically adding commands prior
    # running the device server
    class TangoDeviceServerCommands(object):
        pass

    for req_name, req_doc in requests_dict.items():
        cmd_name = katcpname2tangoname(req_name)
        tango_cmd = create_command2request_handler(req_name, req_doc)
        setattr(TangoDeviceServerCommands, cmd_name, tango_cmd)

    # The device __metaclass__ must be in the final class defination and cannot
    # come from the super class. i.e. The double-definitation
    class TangoDeviceServer(TangoDeviceServerBase, TangoDeviceServerCommands):
        __metaclass__ = DeviceMeta

    return TangoDeviceServer

def main():
    TangoDeviceServer = get_tango_device_server()
    server_run([TangoDeviceServer])

if __name__ == "__main__":
    main()
