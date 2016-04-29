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
 
from katproxy.sim.mkat_ap import MkatApModel, ApOperMode

from PyTango.server import Device, DeviceMeta, command, server_run
from PyTango import AttrWriteType,  DevState
from PyTango import Attr, DevString, DevBoolean, DevDouble
from PyTango import UserDefaultAttrProp, Except, ErrSeverity

MODULE_LOGGER = logging.getLogger(__name__)


class MkatAntennaPositioner(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()
        
    COMMAND_ERROR_REASON = "MkatAntennaPositioner_CommandFailed"
    COMMAND_ERROR_DESC_OFF = "Device in an OFF State"
        
    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.OFF)
        
        self.ap_model = MkatApModel()
        self.ap_model.start()
        
        name = self.get_name()
        self.instances[name] = self
        
    def initialize_dynamic_attributes(self):
        sensors = self.ap_model.get_sensors()
        for sensor in sensors:
            MODULE_LOGGER.debug("Adding mkat_ap sensor %r", sensor.name)
            attr_props = UserDefaultAttrProp()  # Used to set the attribute default properties
            sensor_name = self.formatter(sensor.name)
            method_call_read = None
            method_call_write = None
            
            if sensor.stype == "boolean":
                attr = Attr(sensor_name, DevBoolean, AttrWriteType.READ)
                method_call_read = self.read_attr
            elif sensor.stype == "float":
                if sensor.name.startswith('requested-'):
                    attr = Attr(sensor_name, DevDouble, AttrWriteType.READ_WRITE)
                    method_call_write = self.write_attr
                else:
                    attr = Attr(sensor_name, DevDouble, AttrWriteType.READ)
                method_call_read = self.read_attr
                attr_props.set_min_value(str(sensor.params[0]))
                attr_props.set_max_value(str(sensor.params[1]))
            elif sensor.stype == "discrete":
                attr = Attr(sensor_name, DevString)
                method_call_read = self.read_attr
            
            attr_props.set_label(sensor.name)
            attr_props.set_description(sensor.description)
            attr_props.set_unit(sensor.units)
            attr.set_default_properties(attr_props)
            
            self.add_attribute(attr, method_call_read, method_call_write)
            
    def read_attr(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        sensor_name = self.unformatter(attr.get_name())
        sensor = self.ap_model.get_sensor(sensor_name)
        attr.set_value(sensor.value())    
        
    def write_attr(self, attr):
        pass
    
    def formatter(self, sensor_name):
        """
        Removes the dash(es) in the sensor name and replaces them with underscore(s)
        to guard against illegal attribute identifiers in TANGO
        
        Parameters
        ----------
        sensor_name : str
            The name of the sensor. For example:
            
            'actual-azim'
        
        Returns
        -------
        attr_name : str
            The legal identifier for an attribute. For example:
            
            'actual_azim'
        """
        attr_name = sensor_name.replace('-', '_')
        return attr_name

    def unformatter(self, attr_name):
        """
        Removes the underscore(s) in the attribute name and replaces them with 
        dashe(s), so that we can access the the KATCP Sensors using their identifiers
        
        Parameters
        ----------
        attr_name : str
            The name of the sensor. For example:
            
            'actual_azim'
        
        Returns
        -------
        sensor_name : str
            The legal identifier for an attribute. For example:
            
            'actual-azim'
        """
        sensor_name = attr_name.replace('_', '-')
        return sensor_name
    
    @command
    def TurnOn(self):
        self.set_state(DevState.ON)
        self.ap_model.set_mode(ApOperMode.stop)
        MODULE_LOGGER.info("Turning on the device")
        
    @command
    def TurnOff(self):
        self.set_state(DevState.OFF)
        self.ap_model.set_mode(ApOperMode.shutdown)
        MODULE_LOGGER.info("Turning off the device")
    
    @command
    def Stop(self):
        '''Request mode stop.'''
        command_name = "Stop()"
        if self.get_state() != DevState.OFF:
            if self.ap_model.in_remote_control():
                self.ap_model.set_mode(ApOperMode.stop)
                MODULE_LOGGER.info("Ok")
            else:
                Except.throw_exception(self.COMMAND_ERROR_REASON,
                                       "Antenna is not in remote control", command_name,
                                       ErrSeverity.WARN)
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, self.COMMAND_ERROR_DESC_OFF,
                                   command_name, ErrSeverity.WARN)
               
    @command
    def Maintenance(self):
        command_name = "Maintenance()"
        if self.get_state() != DevState.OFF:
            if self.ap_model.in_remote_control():
                if self.ap_model.mode() in [ApOperMode.gtm, ApOperMode.maint]:
                    Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is"
                                           "in '%s' mode." % self.ap_model.mode(),
                                           command_name, ErrSeverity.WARN)
                elif self.ap_model.mode() not in [ApOperMode.stop]:
                    Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna mode"
                                           "{} != 'stop'.".format(self.ap_model.mode()),
                                           command_name, ErrSeverity.WARN)
                else:
                    self.ap_model.set_mode(ApOperMode.gtm)
                    MODULE_LOGGER.debug("OK")
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON,
                                   self.COMMAND_ERROR_DESC_OFF, command_name,
                                   ErrSeverity.WARN)
        
    @command
    def Stow(self):
        command_name = "Stow()"
        if self.get_state() != DevState.OFF:
            if self.ap_model.in_remote_control():
                if self.ap_model.mode() in [ApOperMode.shutdown, ApOperMode.stowing,
                                            ApOperMode.stowed, ApOperMode.estop]:
                    Except.throw_exception(self.COMMAND_ERROR_REASON,
                                           "Fail, Antenna is in '%s' mode."
                                           % self.ap_model.mode(), command_name,
                                           ErrSeverity.WARN)
                else:
                    self.ap_model.set_mode(ApOperMode.stowing)
                    MODULE_LOGGER.info("OK")
            else:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                       "in remote control.", command_name, 
                                       ErrSeverity.WARN)
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON,
                                   self.COMMAND_ERROR_DESC_OFF, command_name,
                                   ErrSeverity.WARN)
        
    @command
    def Slew(self):
        command_name = "Slew()"
        if self.get_state() != DevState.OFF:
            if self.ap_model.in_remote_control():
                if self.ap_model.mode() not in [ApOperMode.stop, ApOperMode.slew,
                                                ApOperMode.track]:
                    Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Unable to "
                                           "switch Antenna mode to 'slew' while in mode"
                                           "'%s'" % self.ap_model.mode(), command_name,
                                           ErrSeverity.WARN)   
                else:
                    attributes = self.get_device_attr()
                    requested_azim = attributes.get_attr_by_name('requested_azim')
                    requested_elev = attributes.get_attr_by_name('requested_elev')
                    self.ap_model.slew(requested_azim.get_write_value(),
                                       requested_elev.get_write_value())
                    MODULE_LOGGER.info("OK")
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, self.COMMAND_ERROR_DESC_OFF,
                                   command_name, ErrSeverity.WARN)
        
if __name__ == "__main__":
         logging.basicConfig(level=logging.DEBUG)
         server_run([MkatAntennaPositioner])
