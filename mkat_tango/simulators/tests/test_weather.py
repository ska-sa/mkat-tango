import time
import logging

import mock

from random import gauss

from devicetest import DeviceTestCase

# DUT
from mkat_tango.simulators import weather

LOGGER = logging.getLogger(__name__)

LOGGER.debug('Importing')

class AlwaysDifferentGauss(object):

    def __init__(self):
        self.gauss_cache = set([None])

    def __call__(self, *args, **kwargs):
        val = None
        while val in self.gauss_cache:
            val = gauss(*args, **kwargs)
        self.gauss_cache.add(val)
        return val


def read_attributes_as_dicts(dev, attrs):
    result = {}
    for attr in dev.read_attributes(attrs):
        res = result[attr.name] = dict(attr.__dict__)
        res['time'] = attr.time.totime()
    return result

class test_Weather(DeviceTestCase):
    device = weather.Weather
    longMessage = True

    expected_attributes = frozenset([
        'wind_speed', 'wind_direction', 'station_ok',
        'temperature', 'insolation', 'State', 'Status'])

    varying_attributes = frozenset([
        'wind_speed', 'wind_direction', 'temperature', 'insolation'])


    def setUp(self):
        LOGGER.debug('setUp starting')
        # gauss_patcher = mock.patch('mkat_tango.simlib.quantities.gauss')
        # mock_gauss = gauss_patcher.start()
        # self.addCleanup(gauss_patcher.stop)
        # mock_gauss.side_effect = AlwaysDifferentGauss()

        super(test_Weather, self).setUp()
        LOGGER.debug('setUp super done')
        self.instance = weather.Weather.instances[self.device.name()]
        def cleanup_refs(): del self.instance
        self.addCleanup(cleanup_refs)
        LOGGER.debug('setUp done')

    def test_attribute_list(self):
        attributes = set(self.device.get_attribute_list())
        self.assertEqual(attributes, self.expected_attributes)

    def test_varying_attributes_min_interval(self):
        self.maxDiff = None
        model = self.instance.model
        varying_attributes = tuple(self.varying_attributes)
        ## Test that quantities don't change faster than update time
        # Set update time to very long
        model.min_update_period = 999999
        # Cause an initial update
        self.device.State()
        # Get initial values
        initial_vals = read_attributes_as_dicts(self.device, varying_attributes)
        # Ensure that always_executed_hook() is called
        self.device.State()
        later_vals = read_attributes_as_dicts(self.device, varying_attributes)
        # Test that values have not varied
        self.assertEqual(initial_vals, later_vals)

    def test_varying_attributes_update(self):
        self.maxDiff = None
        model = self.instance.model
        varying_attributes = tuple(self.varying_attributes)
        # Get initial values
        LOGGER.debug('Getting init values')
        initial_vals = read_attributes_as_dicts(self.device, varying_attributes)

        ## Test that quantities change after more some time
        # Set update time quite short
        update_period = 0.101
        model.min_update_period = update_period
        # Ensure that always_executed_hook() is called
        self.device.State()
        time.sleep(1.05*update_period)
        # Ensure that always_executed_hook() is called
        self.device.State()
        updated_vals1 = read_attributes_as_dicts(self.device, varying_attributes)
        for attr_name, initial_attr in initial_vals.items():
            updated_attr = updated_vals1[attr_name]
            self.assertNotEqual(updated_attr['value'], initial_attr['value'],
                                "attribute {!r} unchanged after update".format(attr_name))
            dt = updated_attr['time'] - initial_attr['time']
            self.assertGreaterEqual(dt, update_period)

        # TODO
        # 1) check that the values of *each* attribute has changed
        # 2) check that the difference in timestamp is more than update_period

LOGGER.debug('Done Importing')
