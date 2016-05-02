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

from functools import partial

from PyTango import UserDefaultAttrProp
from PyTango import AttrQuality, DevState
from PyTango import Attr, AttrWriteType
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
        self.device_name = 'mkat_sim/' + name.split('/', 1)[1]
        self.device_instance = Weather.instances[self.device_name]
        self.model = self.device_instance.model
        self.set_state(DevState.ON)
        self.dp = PyTango.DeviceProxy(self.device_name)
        self.model_quantities = ''

    def initialize_dynamic_attributes(self):
        weather_sensors = self.dp.get_attribute_list()
        control_attributes = vars(quantities.GaussianSlewLimited(0,0)).keys()
        control_attributes = [attr for attr in control_attributes
                              if not attr.startswith('last')]

        attr_props = UserDefaultAttrProp()
        attr = Attr('sensor_name', DevString, AttrWriteType.READ_WRITE)
	attr.set_default_properties(attr_props)
	self.add_attribute(attr, self.write_attribute)

        for attribute_name in control_attributes:
            MODULE_LOGGER.info(
            "Added weather {} attribute control".format(attribute_name))
            attr_props = UserDefaultAttrProp()
            attr = Attr(attribute_name, DevDouble, AttrWriteType.READ_WRITE)
            attr.set_default_properties(attr_props)
            self.add_attribute(attr, self.write_attributes)

    def write_attribute(self, attr):
        name = attr.get_name()
        attr.set_value(attr.get_write_value())

    def write_attributes(self, attr):
        name = attr.get_name()
        self.info_stream("Writting attribute %s", name)
        attr.set_value(self.model_quantities.__dict__[name])

    def write_sensor_name(self, attr):
        name = attr.get_name()
        data = attr.get_write_value()
	attr.set_value(data)
	self.model_quantities = self.model.sim_quantities[data]

    def write_max_slew_rate(self, attr):
        name = attr.get_name()
	data = attr.get_write_value()
        attr.set_value(data)
        self.model_quantities.__dict__[name] = data

    def write_min_bound(self, attr):
        name = attr.get_name()
        data = attr.get_write_value()
        self.model_quantities.__dict__[name] = data

    def write_max_bound(self, attr):
        name = attr.get_name()
        data = attr.get_write_value()
        self.model_quantities.__dict__[name] = data

    def write_mean(self, attr):
        name = attr.get_name()
        data = attr.get_write_value()
        self.model_quantities.__dict__[name] = data

    def write_std_dev(self, attr):
        name = attr.get_name()
        data = attr.get_write_value()
        self.model_quantities.__dict__[name] = data

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
