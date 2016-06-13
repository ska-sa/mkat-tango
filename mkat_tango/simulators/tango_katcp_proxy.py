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
MeerKAT AP simulator.

    @author MeerKAT CAM team <cam@ska.ac.za>
"""
import weakref

from katcp import kattypes
from PyTango import (DevDouble, DevLong64, DevBoolean, DevString, DevEnum)
from PyTango import Attr, UserDefaultAttrProp, AttrWriteType, DevState
from PyTango.server import Device, DeviceMeta, server_run

KATCP_TYPE_TO_TANGO_TYPE = {
    'integer': DevLong64,
    'float': DevDouble,
    'boolean': DevBoolean,
    'lru': DevString,
    'discrete': DevString,     #TODO (KM) 2016-06-10 : Need to change to DevEnum once solution is found
    'string': DevString,
    'timestamp': DevDouble,
    'address': DevString
}

def kattype2tangotype_object(katcp_sens_type):
    """Convert Tango type object to corresponding kattype type object

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
        raise NotImplementedError("Sensor type deprecated {}"
                                  .format(tango_type))

    return tango_type

def katcp_sensor2tango_attr(sensor):
    """Convert Tango type object to corresponding kattype type object

    Input Parameters
    ----------------
    sensor: A katcp.Sensor object

    Returns
    -------
    attribute: A PyTango.Attr object

    """
    tango_type = kattype2tangotype_object(sensor.stype)
    attr_props = UserDefaultAttrProp()  # Used to set the attribute default properties
    from mkat_ap_tango import formatter
    sensor_name = formatter(sensor.name)

    if sensor.name.startswith('requested-'):
        attribute = Attr(sensor_name, tango_type, AttrWriteType.READ_WRITE)
    else:
        attribute = Attr(sensor_name, tango_type, AttrWriteType.READ)

    if sensor.stype in ['integer', 'float']:
        attr_props.set_min_value(str(sensor.params[0]))
        attr_props.set_max_value(str(sensor.params[1]))

    attr_props.set_label(sensor.name)
    attr_props.set_description(sensor.description)
    attr_props.set_unit(sensor.units)
    attribute.set_default_properties(attr_props)
    return attribute

def update_tango_server_attribute_list(tango_dserver, sensor_list):
    """Populate the TANGO device server attribute list

    Input Parameters
    ----------------
    tango_dserver: An instance of the TangoDeviceServer
    sensor_list: A list of katcp.Sensor objects

    Returns
    -------
    None

    """
    for sensor in sensor_list:
        attribute = katcp_sensor2tango_attr(sensor)
        tango_dserver.add_attribute(attribute)

class TangoDeviceServer(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()

    def init_device(self):
        Device.init_device(self)
        name = self.get_name()
        self.instances[name] = self


class KatcpTango2DeviceProxy(object):
    def __init__(self):
        pass


if __name__ == "__main__":
         server_run([TangoDeviceServer])