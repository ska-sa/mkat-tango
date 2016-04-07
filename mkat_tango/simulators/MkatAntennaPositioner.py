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

from mkat_ap import MkatApModel




from PyTango.server import device_property
from PyTango.server import Device, DeviceMeta, attribute, command, server_run

from PyTango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from PyTango import  Attr, DevFloat, DevString, DevBoolean, DevDouble
from PyTango import UserDefaultAttrProp

class MkatAntennaPositioner(Device):
    __metaclass__ = DeviceMeta
    
    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.OFF)
        
        ap_model = MkatApModel()
        ap_model.start()
        # Get three sensors, one for each data type {boolean, discrete, float}
        sens_mode = ap_model.get_sensor('mode')                   # discrete           
        sens_actual_azim = ap_model.get_sensor('actual-azim')     # float
        sens_fail_prsnt = ap_model.get_sensor('failure-present')  # boolean
    
        sensors = [sens_mode, sens_actual_azim, sens_fail_prsnt]
        
        #attr_props = UserDefaultAttrProp()
        
        
        for sensor in sensors:
            print sensor.name
            attr_props = UserDefaultAttrProp()
            
            if sensor.stype == "boolean":
                attr = Attr(sensor.name, DevBoolean)
            elif sensor.stype == "float":
                attr = Attr(sensor.name, DevDouble, AttrWriteType.READ_WRITE)
                attr_props.set_min_value(str(sensor.params[0]))
                attr_props.set_max_value(str(sensor.params[1]))
            elif sensor.stype == "discrete":
                attr = Attr(sensor.name, DevString)
            
            attr_props.set_label(sensor.name)
            attr_props.set_description(sensor.description)
            attr_props.set_unit(sensor.units)
            attr.set_default_properties(attr_props)
            
            if sensor.stype == "float":
                self.add_attribute(attr, self.read_FloatingPoints)
            elif sensor.stype == "boolean":
                self.add_attribute(attr, self.read_Booleans)
            elif sensor.stype == "discrete":
                self.add_attribute(attr, self.read_Discretes)
           
    
    def read_FloatingPoints(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        attr.set_value(0.0)
        
    def read_Booleans(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        attr.set_value(False)
        
    def read_Discretes(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        attr.set_value("Unknown")    

if __name__ == "__main__":
         server_run([MkatAntennaPositioner])