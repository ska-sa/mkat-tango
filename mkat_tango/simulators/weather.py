import time
import weakref
import logging
import collections

from functools import partial

from PyTango import AttrQuality, DevState
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

class WeatherSimControl(device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary()
    name = self.name()
    device_name = 'mkat_' + name.split('/', 1)[1] + '_simulator'
    device_instance = Weather.instances[device_name]
    self.model = device_instance.model


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
