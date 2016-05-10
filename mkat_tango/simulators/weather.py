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
MeerKAT weather simulator and weather simulator control.
    @author MeerKAT CAM team <cam@ska.ac.za>
    """

import time
import weakref
import logging
import collections
import PyTango
import numpy

from functools import partial

from PyTango import UserDefaultAttrProp
from PyTango import AttrQuality, DevState
from PyTango import Attr, AttrWriteType, WAttribute
from PyTango import DevString, DevDouble, DevBoolean
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command

from mkat_tango.simlib import quantities
from mkat_tango.simlib import model
from mkat_tango.simlib import main

MODULE_LOGGER = logging.getLogger(__name__)


MODULE_LOGGER.debug('Importing')

class Weather(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary() # Access instances for debugging
    DEFAULT_POLLING_PERIOD_MS = int(1 * 1000)

    def init_device(self):
        super(Weather, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        self.model = WeatherModel(name)
        self.set_state(DevState.ON)

    @attribute(label="Current outside temperature", dtype=float,
               min_warning=-5, max_warning=45,
               max_alarm=50, min_alarm=-9,
               unit="Degrees Centigrade",
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def temperature(self):
        value, update_time = self.model.quantity_state['temperature']
        return value, update_time, AttrQuality.ATTR_VALID

    @attribute(label="Wind speed", dtype=float,
               max_warning=15, max_alarm=25,
               unit="m/s",
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def wind_speed(self):
        value, update_time = self.model.quantity_state['wind_speed']
        return value, update_time, AttrQuality.ATTR_VALID

    @attribute(label="Wind direction", dtype=float,
               unit="Degrees",
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def wind_direction(self):
        value, update_time = self.model.quantity_state['wind_direction']
        return value, update_time, AttrQuality.ATTR_VALID

    @attribute(label="Insolation", dtype=float,
               unit="W/m^2",
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def insolation(self):
        value, update_time = self.model.quantity_state['insolation']
        return value, update_time, AttrQuality.ATTR_VALID

    @attribute(label="station_ok", dtype=bool,
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def station_ok(self):
        value, update_time = self.model.quantity_state['station_ok']
        return value, update_time, AttrQuality.ATTR_VALID

    def always_executed_hook(self):
        self.model.update()

class WeatherSimControl(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary()

    def init_device(self):
        super(WeatherSimControl, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        # Get the name of the device
        self.device_name = 'mkat_sim/' + name.split('/', 1)[1]
        self.device_instance = Weather.instances[self.device_name]
        # Get the device instance model to be controlled
        self.model = self.device_instance.model
        # Get a list of attributes a device contains from the model
        self.device_sensors = self.model.sim_quantities.keys()
        self.set_state(DevState.ON)
        self.model_quantities = None
        self._sensor_name = ''
        self._pause_active = False

    # Static attributes of the device

    @attribute(dtype=str)
    def sensor_name(self):
        return self._sensor_name

    @sensor_name.write
    def sensor_name(self, name):
        if name in self.device_sensors:
            self._sensor_name = name
            self.model_quantities = self.model.sim_quantities[self._sensor_name]
        else:
            raise NameError('Name does not exist in the sensor list {}'.
                            format(self.device_sensors))

    @attribute(dtype=bool)
    def pause_active(self):
        return self._pause_active

    @pause_active.write
    def pause_active(self, isActive):
        self._pause_active = isActive
        setattr(self.model, 'paused', isActive)

    def initialize_dynamic_attributes(self):
        '''The device method that sets up attributes during run time'''
        # Get attributes to control the device model quantities
        # from class variables of the quantities included in the device model.
        models = set([quant.__class__
                      for quant in self.model.sim_quantities.values()])
        control_attributes = []

        for cls in models:
            control_attributes += [attr for attr in cls.adjustable_attributes]

        # Add a list of float attributes from the list of Guassian variables
        for attribute_name in control_attributes:
            MODULE_LOGGER.info(
            "Added weather {} attribute control".format(attribute_name))
            attr_props = UserDefaultAttrProp()
            attr = Attr(attribute_name, DevDouble, AttrWriteType.READ_WRITE)
            attr.set_default_properties(attr_props)
            self.add_attribute(attr, self.read_attributes, self.write_attributes)

    def read_attributes(self, attr):
        '''Method reading an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to read from.
        '''
        name = attr.get_name()
        self.info_stream("Reading attribute %s", name)
        attr.set_value(getattr(self.model_quantities, name))

    def write_attributes(self, attr):
        '''Method writing an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to write to.
        '''
        name = attr.get_name()
        data = attr.get_write_value()
        self.info_stream("Writing attribute {} with value: {}".format(name, data))
        attr.set_value(data)
        setattr(self.model_quantities, name, data)
        if name == 'last_val' and self._pause_active:
            self.model.quantity_state[self._sensor_name] = data, time.time()
        else:
            setattr(self.model_quantities, name, data)

class WeatherModel(model.Model):

    def setup_sim_quantities(self):
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)
        self.sim_quantities.update(dict(
            temperature=GaussianSlewLimited(
                mean=20, std_dev=20, max_slew_rate=5,
                min_bound=-10, max_bound=55),
            wind_speed=GaussianSlewLimited(
                mean=1, std_dev=20, max_slew_rate=3,
                min_bound=0, max_bound=100),
            wind_direction=GaussianSlewLimited(
                mean=0, std_dev=150, max_slew_rate=60,
                min_bound=0, max_bound=359.9999),
            insolation=GaussianSlewLimited(
                mean=500, std_dev=1000, max_slew_rate=100,
                min_bound=0, max_bound=1100),
            station_ok=ConstantQuantity(start_value=True)

        ))
        super(WeatherModel, self).setup_sim_quantities()


weather_main = partial(main.simulator_main, Weather, WeatherSimControl)

if __name__ == "__main__":
    weather_main()
