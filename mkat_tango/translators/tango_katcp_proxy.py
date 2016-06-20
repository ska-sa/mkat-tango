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
import weakref
import logging
import tornado

from katcp import inspecting_client, ioloop_manager

from utilities import katcpname2tangoname, tangoname2katcpname

from PyTango import DevDouble, DevLong64, DevBoolean, DevString, DevFailed, DevState
from PyTango import Attr, UserDefaultAttrProp, AttrWriteType
from PyTango.server import Device, DeviceMeta
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

def kattype2tangotype_object(katcp_sens_type):
    """Convert KATCP Sensor type to A corresponding TANGO type object

    Input Parameters
    ----------------
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

    Input Parameters
    ----------------
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
        attr_props.set_min_value(str(sensor.params[0]))
        attr_props.set_max_value(str(sensor.params[1]))

    attr_props.set_label(sensor.name)
    attr_props.set_description(sensor.description)
    #attr_props.set_unit(sensor.units)      # Seems to cause a seg fault when starting DS
    attribute.set_default_properties(attr_props)
    return attribute

def add_tango_server_attribute_list(tango_dserver, sensors):
    """Add in new TANGO attributes.

    Input Parameters
    ----------------
    tango_dserver: A PyTango.TangoDeviceServer instance
        Tango Attributes mirroring the KATCP sensors in sensor_list are added to
        tango_dserver.
    sensors: dict()
        A dictionary mapping sensor names to katcp.Sensor objects.

    Returns
    -------
    None

    """
    for sensor in sensors:
        attribute = katcp_sensor2tango_attr(sensors[sensor])
        tango_dserver.add_attribute(attribute, tango_dserver.read_attr)

def remove_tango_server_attribute_list(tango_dserver, sensors):
    """Remove existing TANGO attributes.

    Input Parameters
    ----------------
    tango_dserver: A PyTango.TangoDeviceServer instance
        Tango Attributes mirroring the KATCP sensors in sensor_list are added to
        tango_dserver.
    sensors: dict()
        A dictionary mapping sensor names to katcp.Sensor objects

    Returns
    -------
    None

    """
    for sensor in sensors:
        attr_name = katcpname2tangoname(sensors[sensor].name)
        try:
            tango_dserver.remove_attribute(attr_name)
        except DevFailed:
            MODULE_LOGGER.debug("Attribute {} does not exist".format(attr_name))

class TangoDeviceServer(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()

    katcp_address = device_property(dtype=str, doc=
            'katcp address of the device to translate as <host>:<port>')

    def __init__(self, *args, **kwargs):
        self.tango_katcp_proxy = None
        Device.__init__(self, *args, **kwargs)

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

    def read_attr(self, attr):
        '''Read value for an attribute from the AP model into the Tango attribute

        Parameters
        ==========
        attribute : PyTango.Attribute
            The attribute into which the value is read from the AP model.

        Note: `attr` is modified in place.

        '''
        name = attr.get_name()
        self.info_stream("Reading attribute %s", name)
        sensor_value = self.tango_katcp_proxy._observers[name].updates[0][1].value
        attr.set_value(sensor_value)

class KatcpTango2DeviceProxy(object):
    def __init__(self, katcp_inspecting_client, tango_device_server, ioloop):
        self.katcp_inspecting_client = katcp_inspecting_client
        self.tango_device_server = tango_device_server
        self.ioloop = ioloop
        self._current_sensors = dict()
        self._observers = dict()

    def start(self):
        """Start the translator

        Starts the KATCP inspecting client

        """
        self.katcp_inspecting_client.set_state_callback(self.katcp_state_callback)
        self.ioloop.add_callback(self.katcp_inspecting_client.connect)

    def stop(self, timeout=1.0):
        """Stop the KATCP inspecting client

        """
        self.katcp_inspecting_client.stop(timeout=timeout)

    def join(self, timeout=None):
        self.katcp_inspecting_client.join(timeout=timeout)

    @tornado.gen.coroutine
    def katcp_state_callback(self, state, model_changes):
        if model_changes:
            try:
                removed_sensors = model_changes['sensors']['removed']
                added_sensors = model_changes['sensors']['added']
            except KeyError:
                pass
            else:
                self.reconfigure_tango_device_server(removed_sensors, added_sensors)

    @tornado.gen.coroutine
    def reconfigure_tango_device_server(self, removed_sens, added_sens):
        removed_sensors = dict()
        for sens_name in removed_sens:
            sensor = yield self.katcp_inspecting_client.future_get_sensor(sens_name)
            tango_name = katcpname2tangoname(sens_name)
            removed_sensors[tango_name] = sensor
        remove_tango_server_attribute_list(self.tango_device_server,
                                           removed_sensors)

        added_sensors = dict()
        for sens_name in added_sens:
            sensor = yield self.katcp_inspecting_client.future_get_sensor(sens_name)
            tango_name = katcpname2tangoname(sens_name)
            if tango_name not in self._observers.keys():
                self._observers[tango_name] = observer = SensorObserver()
                sensor.attach(observer)
            added_sensors[tango_name] = sensor
        add_tango_server_attribute_list(self.tango_device_server, added_sensors)
        self._update_existing_sensor_dict(added_sensors, removed_sensors)

        for sensor_name in self._current_sensors.keys():
            reply, informs = yield self.katcp_inspecting_client.simple_request(
                    'sensor-sampling',
                    tangoname2katcpname(sensor_name),
                    'event')
            if not reply.reply_ok():
                MODULE_LOGGER.debug("Unexpected failure reply for {} sensor".format(
                    sensor_name))

    def _update_existing_sensor_dict(self, added_sensors, removed_sensors):
        for sens_name in removed_sensors:
            self._current_sensors.pop(sens_name)
        self._current_sensors.update(added_sensors)

    @classmethod
    def from_katcp_address_tango_device(cls,
            katcp_server_address, tango_device_server):
        """Instatiate KatcpTango2DeviceProxy from network address

        Parameters
        =========
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
    def __init__(self):
        self.updates = []

    def update(self, sensor, reading):
        if len(self.updates) > 0:
            self.updates.pop()
        self.updates.append((sensor, reading))
        MODULE_LOGGER.debug('Received {!r} for attr {!r}'.format(sensor, reading))

if __name__ == "__main__":
    server_run([TangoDeviceServer])
