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

from mkat_tango.translators.utilities import katcpname2tangoname

from PyTango import DevDouble, DevLong64, DevBoolean, DevString, DevFailed
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
    attr_props.set_unit(sensor.units)
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

    def read_attributes(self, attr):
        '''Method reading an attribute value

        Parameters
        ==========
        attr : PyTango.DevAttr
        The attribute to read from.

        '''
        name = attr.get_name()
        self.info_stream("Reading attribute %s", name)
        attr.set_value(getattr(sensor_list[name], 'value'))

    if remove_attr:
        for sensor in sensor_list:
            attr_name = katcpname2tangoname(sensor.name)
            try:
                tango_dserver.remove_attribute(attr_name)
            except DevFailed:
                MODULE_LOGGER.debug("Attribute {} does not exist".format(attr_name))
    else:
        for sensor in sensor_list:
            attribute = katcp_sensor2tango_attr(sensor)
            tango_dserver.add_attribute(attribute, read_attributes)
            # TODO (KM) 2016-06-14: Have to provide a read method for the attributes

class TangoDeviceServer(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()

    katcp_address = device_property(dtype=str, doc=
            'katcp address of the device to translate as <host>:<port>')

    def __init__(self, *args, **kwargs):
        Device.__init__(self, *args, **kwargs)
        self.katcp_tango_proxy = None

    def init_device(self):
        if self.katcp_tango_proxy:
            self.katcp_tango_proxy.ioloop.add_callback(
                    self.katcp_tango_proxy.ioloop.stop)
        Device.init_device(self)
        name = self.get_name()
        self.instances[name] = self


class KatcpTango2DeviceProxy(object):
    def __init__(self):
        pass


if __name__ == "__main__":
         server_run([TangoDeviceServer])
