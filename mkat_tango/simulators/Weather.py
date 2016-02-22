import time
import weakref
import logging
import collections

from functools import partial

from PyTango import AttrQuality
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command

from mkat_tango.simlib import quantities
from mkat_tango.simlib import model
from mkat_tango.simlib import main

MODULE_LOGGER = logging.getLogger(__name__)

class Weather(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary() # Access instances for debugging
    DEFAULT_POLLING_PERIOD_MS = int(1 * 1000)

    def init_device(self):
        super(Weather, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        self.model = WeatherModel(name)

    @attribute(label="Current outside temperature", dtype=float,
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def temperature(self):
        value, update_time = self.model.quantity_state['temperature']
        return value, update_time, AttrQuality.ATTR_VALID

    @attribute(label="Wind speed", dtype=float,
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def wind_speed(self):
        value, update_time = self.model.quantity_state['wind_speed']
        return value, update_time, AttrQuality.ATTR_VALID

    @attribute(label="Wind direction", dtype=float,
               polling_period=DEFAULT_POLLING_PERIOD_MS)
    def wind_direction(self):
        value, update_time = self.model.quantity_state['wind_direction']
        return value, update_time, AttrQuality.ATTR_VALID

    def always_executed_hook(self):
        self.model.update()


class WeatherModel(model.Model):

    def setup_sim_quantities(self):
        start_time = self.start_time
        self.sim_quantities.update(dict(
            temperature=quantities.GaussianSlewLimited(
                mean=20, std_dev=20, max_slew_rate=1./100,
                min_bound=-10, max_bound=55,
                start_time=start_time),
            wind_speed=quantities.GaussianSlewLimited(
                mean=1, std_dev=20, max_slew_rate=3,
                min_bound=0, max_bound=100,
                start_time=start_time),
            wind_direction=quantities.GaussianSlewLimited(
                mean=0, std_dev=600, max_slew_rate=180,
                min_bound=0, max_bound=359.9999,
                start_time=start_time),
        ))
        super(WeatherModel, self).setup_sim_quantities()


weather_main = partial(main.simulator_main, Weather)
