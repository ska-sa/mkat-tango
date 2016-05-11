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
from katcp import Sensor
from PyTango import DeviceProxy, CmdArgType,DevState
from tango_inspecting_client import TangoInspectingClient


def tango_attribute_descr2katcp_sensor(tango_attribute_descr):
    """Convert a tango attribute description into an equivalent KATCP Sensor object
    
    Parameters
    ==========

    tango_attribute_descr : PyTango.AttributeInfoEx data structure  
    
    Return Value
    ============
    sensor: katcp.Sensor object
    
    """
    
    sensor_type = None
    sensor_params = None 
    
    if tango_attribute_descr.data_type == CmdArgType.DevDouble:
        sensor_type = Sensor.FLOAT
        sensor_params = [float(tango_attribute_descr.min_value), 
                         float(tango_attribute_descr.max_value)]
    elif tango_attribute_descr.data_type == CmdArgType.DevBoolean:
        sensor_type = Sensor.BOOLEAN
    elif tango_attribute_descr.data_type == CmdArgType.DevState:
        sensor_type = Sensor.DISCRETE
        state_enums = DevState.names
        state_possible_vals = state_enums.keys()
        sensor_params = state_possible_vals
    elif tango_attribute_descr.data_type == CmdArgType.DevString:
        # TODO Should be DevEnum in Tango9. For now don't create sensor object
        return None
        #sensor_type = Sensor.DISCRETE
        #sensor_params = attr_name.enum_labels
    
    return Sensor(sensor_type, tango_attribute_descr.name, tango_attribute_descr.description, 
                  tango_attribute_descr.unit, sensor_params)


dp = DeviceProxy('test/mkat_ap_tango/1')
tic = TangoInspectingClient(dp)
attrs = tic.inspect_attributes()
             
sensors = {}

for attr_name in attrs.keys(): 
    sensors[attr_name] = tango_attribute_descr2katcp_sensor(attrs[attr_name])
