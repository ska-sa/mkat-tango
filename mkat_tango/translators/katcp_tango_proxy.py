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
from PyTango import CmdArgType, DevState, AttrDataFormat

def tango_attr_descr2katcp_sensor(tango_attr_descr):
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

    if tango_attr_descr.data_format != AttrDataFormat.SCALAR:
        raise NotImplementedError("KATCP complexity with non-scalar data formats")

    if (tango_attr_descr.data_type == CmdArgType.DevDouble or
        tango_attr_descr.data_type == CmdArgType.DevFloat):
        sensor_type = Sensor.FLOAT
        sensor_params = [float(tango_attr_descr.min_value),
                         float(tango_attr_descr.max_value)]
    elif tango_attr_descr.data_type == CmdArgType.DevBoolean:
        sensor_type = Sensor.BOOLEAN
    elif tango_attr_descr.data_type == CmdArgType.DevState:
        sensor_type = Sensor.DISCRETE
        state_enums = DevState.names
        state_possible_vals = state_enums.keys()
        sensor_params = state_possible_vals
    elif (tango_attr_descr.data_type == CmdArgType.DevString or
        tango_attr_descr.data_type == CmdArgType.DevEnum):
        # TODO Should be DevEnum in Tango9. For now don't create sensor object
        #sensor_type = Sensor.DISCRETE
        #sensor_params = attr_name.enum_labels
        raise NotImplementedError("Cannot create DISCRETE sensors from the DevEnum"
                                   "/DevString attributes yet! Tango9 feature issue")
    else:
        raise NotImplementedError("Unhandled attribute type {!r}"
                                  .format(tango_attr_descr.data_type))


    return Sensor(sensor_type, tango_attr_descr.name,
                  tango_attr_descr.description,
                  tango_attr_descr.unit, sensor_params)
