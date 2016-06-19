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
    attr_props.set_unit(sensor.units)      # Seems to cause a seg fault when starting DS
    attribute.set_default_properties(attr_props)
    return attribute

def update_tango_server_attribute_list(tango_dserver, sensor_list, remove_attr=False):
    """Add in new TANGO attributes or remove existing attributes

    Input Parameters
    ----------------
    tango_dserver: A PyTango.TangoDeviceServer instance
        Tango Attributes mirroring the KATCP sensors in sensor_list are added to
        tango_dserver.
    sensor_list: A list of katcp.Sensor objects

    Returns
    -------
    None

    """
    if remove_attr:
        for sensor in sensor_list:
            attr_name = katcpname2tangoname(sensor_list[sensor].name)
            try:
                tango_dserver.remove_attribute(attr_name)
            except DevFailed:
                MODULE_LOGGER.debug("Attribute {} does not exist".format(attr_name))
    else:
        for sensor in sensor_list:
            attribute = katcp_sensor2tango_attr(sensor_list[sensor])
            tango_dserver.add_attribute(attribute, tango_dserver.read_attr)
            # TODO (KM) 2016-06-14: Have to provide a read method for the attributes


class TangoDeviceServer(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()

    katcp_address = device_property(dtype=str, doc=
            'katcp address of the device to translate as <host>:<port>')

    def __init__(self, *args, **kwargs):
        self.katcp_tango_proxy = None
        Device.__init__(self, *args, **kwargs)

    def init_device(self):
        if self.katcp_tango_proxy:
            self.katcp_tango_proxy.ioloop.add_callback(
                    self.katcp_tango_proxy.ioloop.stop)

        Device.init_device(self)
        self.set_state(DevState.ON)
        name = self.get_name()
        self.instances[name] = self
        katcp_host, katcp_port = self.katcp_address.split(':')
        katcp_port = int(katcp_port)
        self.katcp_tango_proxy = (
                KatcpTango2DeviceProxy.from_katcp_address_tango_device(
                    (katcp_host, katcp_port), self))
        self.katcp_tango_proxy.start()

    def read_attr(self, attr):
        '''Read value for an attribute from the AP model into the Tango attribute

        Parameters
        ==========
        attribute : PyTango.Attribute
            The attribute into which the value is read from the AP model.

        Note: `attr` is modified in place.

        '''
        self.info_stream("Reading attribute %s", attr.get_name())
        sens = self.katcp_tango_proxy._current_sensors
        sensor_name = tangoname2katcpname(attr.get_name())
        sensor = sens[sensor_name]
        attr.set_value(sensor.value())

class KatcpTango2DeviceProxy(object):
    def __init__(self, katcp_inspecting_client, tango_device_server, ioloop):
        self.katcp_inspecting_client = katcp_inspecting_client
        self.tango_device_server = tango_device_server
        self.ioloop = ioloop
        self._current_sensors = {}

    def start(self):
        """Start the translator

        Starts the KATCP inspecting client

        """
        self.katcp_inspecting_client.set_state_callback(self.katcp_state_callback)
        self.ioloop.add_callback(self.katcp_inspecting_client.connect)

    def stop(self, timeout=1.0):
        """Stop the translator

        At the moment only the KATCP component is stopped since we don't yet
        know how to stop the Tango DeviceProxy. Some thread leakage therefore to
        be expected :(

        """
        self.katcp_inspecting_client.stop(timeout=timeout)

    def join(self, timeout=None):
        self.katcp_inspecting_client.join(timeout=timeout)

    @tornado.gen.coroutine
    def katcp_state_callback(self, *args, **kwargs):
        if args[1]:
            try:
                removed_sensors = args[1]['sensors']['removed']
                added_sensors = args[1]['sensors']['added']
            except KeyError:
                pass
            else:
                self.reconfigure_tango_device_server(removed_sensors, added_sensors)

    @tornado.gen.coroutine
    def reconfigure_tango_device_server(self, removed_sens, added_sens):
        removed_sensor_list = dict()
        for sens_name in removed_sens:
            sensor = yield self.katcp_inspecting_client.future_get_sensor(sens_name)
            removed_sensor_list[sens_name] = sensor
        update_tango_server_attribute_list(self.tango_device_server,
                                           removed_sensor_list, remove_attr=True)

        added_sensor_list = dict()
        for sens_name in added_sens:
            sensor = yield self.katcp_inspecting_client.future_get_sensor(sens_name)
            added_sensor_list[sens_name] = sensor
        update_tango_server_attribute_list(self.tango_device_server, added_sensor_list)
        self._update_existing_sensor_list(added_sensor_list, removed_sensor_list)

    def _update_existing_sensor_list(self, added, removed):
        for sens_name in removed:
            self._current_sensors.pop(sens_name)
        self._current_sensors.update(added)

    @classmethod
    def from_katcp_address_tango_device(cls,
            katcp_server_address, tango_device_server):
        """Instatiate KatcpTango2DeviceProxy from network address

        Parameters
        =========
        katcp_server_address : tuple (hostname : str, port, port : int)
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

if __name__ == "__main__":
    server_run([TangoDeviceServer])
