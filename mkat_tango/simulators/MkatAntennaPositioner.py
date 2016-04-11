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
import logging
import weakref


from mkat_ap import MkatApModel, ApOperMode

from PyTango.server import device_property
from PyTango.server import Device, DeviceMeta, attribute, command, server_run

from PyTango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from PyTango import  Attr, DevFloat, DevString, DevBoolean, DevDouble
from PyTango import UserDefaultAttrProp

MODULE_LOGGER = logging.getLogger(__name__)

class MkatAntennaPositioner(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()
        
    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.OFF)
        
        self.ap_model = MkatApModel()
        self.ap_model.start()
        
        name = self.get_name()
        self.instances[name] = self
        
        # Get three sensors, one for each data type {boolean, discrete, float}
        sensors = self.ap_model.get_sensors()
        
        for sensor in sensors:
            
            MODULE_LOGGER.info(sensor.name)
            attr_props = UserDefaultAttrProp()
            sensor_name = self.formatter(sensor.name)
            method_call_read = None
            method_call_write = None
            
            if sensor.stype == "boolean":
                attr = Attr(sensor_name, DevBoolean)
                method_call_read = self.read_Booleans
            elif sensor.stype == "float":
                if sensor.name.startswith('actual-'): #== 'actual-azim' or sensor.name == 'actual-elev':
                    attr = Attr(sensor_name, DevDouble, AttrWriteType.READ)
                else:
                    attr = Attr(sensor_name, DevDouble, AttrWriteType.READ_WRITE)
                    method_call_write = self.write_FloatingPoints
                method_call_read = self.read_FloatingPoints
                attr_props.set_min_value(str(sensor.params[0]))
                attr_props.set_max_value(str(sensor.params[1]))
            elif sensor.stype == "discrete":
                attr = Attr(sensor_name, DevString)
                method_call_read = self.read_Discretes
            
            attr_props.set_label(sensor.name)
            attr_props.set_description(sensor.description)
            attr_props.set_unit(sensor.units)
            attr.set_default_properties(attr_props)
            
            self.add_attribute(attr, method_call_read, method_call_write)           
            
    
    def read_FloatingPoints(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        sens_name = self.unformatter(attr.get_name())
        actual_azim_sens = self.ap_model.get_sensor(sens_name)
        attr.set_value(actual_azim_sens.value())

    def write_FloatingPoints(self, attr):
        name = attr.get_name()
        data = attr.get_write_value()
        self.info_stream("Writting into attribute %s the value %s", name, data)
        sens_name = self.unformatter(name)
        sens = self.ap_model.get_sensor(sens_name)
        sens.set_value(data)
        
    def read_Booleans(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        sens_name = self.unformatter(attr.get_name())
        actual_azim_sens = self.ap_model.get_sensor(sens_name)
        attr.set_value(actual_azim_sens.value())
        
    def read_Discretes(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        sens_name = self.unformatter(attr.get_name())
        actual_azim_sens = self.ap_model.get_sensor(sens_name)
        attr.set_value(actual_azim_sens.value())    
    
    def formatter(self, sensor_name):
        attr_name = sensor_name.replace('-', '_')
        return attr_name

    def unformatter(self, attr_name):
        sensor_name = attr_name.replace('_', '-')
        return sensor_name
    
    
    @command
    def Stop(self):
        '''Set the simulator operation mode to slew to desired coordinates.'''
        if self.ap_model.in_remote_control():
            self.ap_model.set_mode(ApOperMode.stop)
            MODULE_LOGGER.info("Ok")
        else:
            MODULE_LOGGER.info("Fail, Antenna is not in remote control.")
            
            
    @command
    def Maintenance(self):
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() in [ApOperMode.gtm, ApOperMode.maint]:
                MODULE_LOGGER.info("Fail, Antenna is in '%s' mode." % self.ap_model.mode())
            elif self.ap_model.mode() not in [ApOperMode.stop]:
                MODULE_LOGGER.info("Fail, Antenna mode {} != 'stop'.".format(self.ap_model.mode()))
            else:
                self.ap_model.set_mode(ApOperMode.gtm)
        else:
            MODULE_LOGGER.info("Fail, Antenna is not in remote control.")
            
            
    @command
    def Stow(self):
        if self.ap_model.in_remote_control():
            if (self.ap_model.mode() in [ApOperMode.shutdown, ApOperMode.stowing,
                ApOperMode.stowed, ApOperMode.estop]):
                    MODULE_LOGGER.info("Fail, Antenna is in '%s' mode." % self.ap_model.mode())
            else:
                self.ap_model.set_mode(ApOperMode.stowing)
                MODULE_LOGGER.info("Ok")
        else:
            MODULE_LOGGER.info("Fail, Antenna is not in remote control.")
    
    @command
    def Rate(self):
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() not in [ApOperMode.stop]:
                MODULE_LOGGER.info("Fail, Antenna mode '%s' != 'stop'." % self.ap_model.mode())
            else:
                requested_azim_rate = self.get_device_attr().get_attr_by_name('requested_azim_rate')
                requested_elev_rate = self.get_device_attr().get_attr_by_name('requested_elev_rate')
                self.ap_model.rate(requested_azim_rate.get_write_value(), requested_elev_rate.get_write_value())
                MODULE_LOGGER.info("Ok")
        else:
            MODULE_LOGGER.info("Fail, Antenna is not in remote control.")
            
    @command
    def Slew(self):
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() not in [ApOperMode.stop, ApOperMode.slew, ApOperMode.track]:
                MODULE_LOGGER.info("Fail, Unable to switch Antenna mode to 'slew' while in mode '%s'" % self.ap_model.mode())
            else:
                requested_azim = self.get_device_attr().get_attr_by_name('requested_azim')
                requested_elev = self.get_device_attr().get_attr_by_name('requested_elev')
                self.ap_model.slew(requested_azim.get_write_value(), requested_elev.get_write_value())
                MODULE_LOGGER.info("Ok")
                
if __name__ == "__main__":
         logging.basicConfig(level=logging.DEBUG)
         server_run([MkatAntennaPositioner])
