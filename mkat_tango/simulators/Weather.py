import time
import sys
import weakref
import logging
import threading
import collections

from PyTango import AttrQuality
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command
from PyTango.server import server_run


from mkat_tango.simlib import quantities

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


class WeatherModel(object):
    def __init__(self, name, start_time=None, min_update_time=9+0.9,
                 time_func=time.time):
        self.name = name
        self.min_update_time = min_update_time
        self.time_func = time_func
        start_time = start_time or time_func()
        self.last_update_time = start_time
        self.sim_quantities = dict(
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
        )

        self._sim_state = {var: (quant.last_val, quant.last_update_time)
                          for var, quant in self.sim_quantities.items()}

        # NM: Making a public reference to _sim_state. Allows us to hook read-only views
        # or updates or whatever the future requires of this humble public attribute.
        self.quantity_state = self._sim_state

    def update(self):
        sim_time = self.time_func()
        dt = sim_time - self.last_update_time
        if dt < self.min_update_time:
            MODULE_LOGGER.debug(
                "Sim {} skipping update at {}, dt {} < {}"
                .format(self.name, sim_time, dt, self.min_update_time))
            return

        MODULE_LOGGER.info("Stepping at {}, dt: {}".format(sim_time, dt))
        self.last_update_time = sim_time
        try:
            for var, quant in self.sim_quantities.items():
                self._sim_state[var] = (quant.next_val(sim_time), sim_time)
        except Exception:
            MODULE_LOGGER.exception('Exception in update loop')


def weather_main():
    run_ipython = '--ipython' in sys.argv
    if run_ipython:
        import IPython
        sys.argv.remove('--ipython')
        def run_ipython():
            IPython.embed()
        t = threading.Thread(target=run_ipython)
        t.setDaemon(True)
        t.start()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - '
        '%(pathname)s : %(lineno)d - %(message)s',
        level=logging.INFO)

    server_run([Weather])
