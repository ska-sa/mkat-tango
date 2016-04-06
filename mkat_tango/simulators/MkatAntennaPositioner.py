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


import time
import numpy
import threading
import logging

from functools import partial


from PyTango.server import device_property
from PyTango.server import Device, DeviceMeta, attribute, command, server_run

from PyTango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt, Attr, DevFloat, DevString, DevBoolean, DevDouble
from PyTango import UserDefaultAttrProp

class MkatAntennaPositioner(Device):
    __metaclass__ = DeviceMeta
    
    #voltage = attribute()   
    
    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.STANDBY)
        
        ap_model = MkatApModel()
        #ap_model.start()
        print "starting"
        sensors = ap_model.get_sensors()
        
        attr_props = UserDefaultAttrProp()
        
        for sensor in sensors:
            print sensor.name
#            if sensor.stype == "boolean":
#                attr = Attr(sensor.name, DevBoolean)
#            elif sensor.stype == "float":
#                attr = Attr(sensor.name, DevFloat)
#            elif sensor.stype == "discrete":
#                attr = Attr(sensor.name, DevString)
            
            attr = Attr(sensor.name, DevDouble)
            attr_props.set_label(sensor.name)
            attr_props.set_description(sensor.description)
            attr_props.set_unit(sensor.units)
            attr.set_default_properties(attr_props)
            
            self.add_attribute(attr)


if __name__ == "__main__":
         server_run([MkatAntennaPositioner])