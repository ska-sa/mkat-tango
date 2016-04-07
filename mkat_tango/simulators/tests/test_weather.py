import time
import logging

from devicetest import DeviceTestCase

# DUT
from mkat_tango.simulators import weather

LOGGER = logging.getLogger(__name__)

def read_attributes_as_dicts(dev, attrs):
    result = {}
    for attr in dev.read_attributes(attrs):
        res = result[attr.name] = dict(attr.__dict__)
        res['time'] = attr.time.totime()
    return result

class test_Weather(DeviceTestCase):
    device = weather.Weather

    expected_attributes = frozenset([
        'wind_speed', 'wind_direction', 'station_ok',
        'temperature', 'insolation', 'State', 'Status'])

    varying_attributes = frozenset([
        'wind_speed', 'wind_direction', 'temperature', 'insolation'])

    def setUp(self):
        super(test_Weather, self).setUp()
        self.instance = weather.Weather.instances[self.device.name()]
        def cleanup_refs(): del self.instance
        self.addCleanup(cleanup_refs)

    def test_attribute_list(self):
        attributes = set(self.device.get_attribute_list())
        self.assertEqual(attributes, self.expected_attributes)

    def test_varying_attributes(self):
        self.maxDiff = None
        model = self.instance.model
        varying_attributes = tuple(self.varying_attributes)
        ## Test that quantities don't change faster than update time
        # Set update time to very long
        model.min_update_time = 999999
        # Cause an initial update
        self.device.State()
        # Get initial values
        initial_vals = read_attributes_as_dicts(self.device, varying_attributes)
        # Ensure that always_executed_hook() is called
        self.device.State()
        later_vals = read_attributes_as_dicts(self.device, varying_attributes)
        # Test that values have not varied
        self.assertEqual(initial_vals, later_vals)

        ## Test that quantities change if update time is reduced
        # Set update time quite short
        update_time = 0.001
        model.min_update_time = update_time
        time.sleep(3*update_time)
        # Ensure that always_executed_hook() is called
        self.device.State()
        updated_vals = read_attributes_as_dicts(self.device, varying_attributes)

        # TODO
        # 1) check that the values of *each* attribute has changed
        # 2) check that the difference in timestamp is more than update_time
