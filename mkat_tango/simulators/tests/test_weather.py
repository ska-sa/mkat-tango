###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
from future import standard_library
standard_library.install_aliases()
from builtins import object
import time
import logging
import mock
import unittest

from random import gauss

from tango.test_context import DeviceTestContext

from mkat_tango.testutils import disable_attributes_polling

# DUT
from mkat_tango.simulators import weather

LOGGER = logging.getLogger(__name__)

class AlwaysDifferentGauss(object):

    def __init__(self):
        self.gauss_cache = set([None])

    def __call__(self, *args, **kwargs):
        val = None
        while val in self.gauss_cache:
            val = gauss(*args, **kwargs)
        self.gauss_cache.add(val)
        return val

def never_repeat(fn):
    """Decorate random quantity next_value() to prevent any value from repeating"""
    cache = set()

    def decorated_fn(*args, **kwargs):
        quant = fn.__self__
        last_update_time = quant.last_update_time
        val = fn(*args, **kwargs)
        i = 0
        while val in cache:
            quant.last_update_time = last_update_time
            val = fn(*args, **kwargs)
            LOGGER.debug('Got {!r} from {!r}'.format(val, fn))
            i += 1
            if i > 5000:
                LOGGER.error('Could not get a unique value from {!r}'.format(fn))
                break

        cache.add(val)
        return val

    return decorated_fn

def read_attributes_as_dicts(dev, attrs):
    result = {}
    for attr in dev.read_attributes(attrs):
        res = result[attr.name] = dict(attr.__dict__)
        res['time'] = attr.time.totime()
    return result


class test_Weather(unittest.TestCase):
    device = weather.Weather
    longMessage = True

    expected_attributes = frozenset([
        'wind-speed', 'wind-direction', 'input-comms-ok',
        'temperature', 'insolation', 'State', 'Status',
        'rainfall', 'relative-humidity', 'pressure'])

    varying_attributes = frozenset([
        'wind-speed', 'wind-direction', 'temperature', 'insolation',
        'rainfall', 'relative-humidity', 'pressure'])

    @classmethod
    def setUpClass(cls):
        cls.tango_context = DeviceTestContext(cls.device)
        cls.tango_context.start()

    def setUp(self):
        super(test_Weather, self).setUp()
        self.tango_dp = self.tango_context.device
        self.instance = weather.Weather.instances[self.tango_dp.name()]
        def cleanup_refs(): del self.instance
        self.addCleanup(cleanup_refs)

    @classmethod
    def tearDownClass(cls):
        """Kill the device server."""
        cls.tango_context.stop()

    def test_attribute_list(self):
        attributes = set(self.tango_dp.get_attribute_list())
        self.assertEqual(attributes, self.expected_attributes)

    def test_varying_attributes_min_interval(self):
        # Test that attributes do not change within the minimum model update period

        self.maxDiff = None
        model = self.instance.model
        varying_attributes = tuple(self.varying_attributes)
        ## Test that quantities don't change faster than update time
        # Set update time to very long
        model.min_update_period = 999999
        # Cause an initial update
        self.tango_dp.State()
        # Get initial values
        initial_vals = read_attributes_as_dicts(self.tango_dp, varying_attributes)
        # Ensure that always_executed_hook() is called
        self.tango_dp.State()
        later_vals = read_attributes_as_dicts(self.tango_dp, varying_attributes)
        # Test that values have not varied
        self.assertEqual(initial_vals, later_vals)

    def test_varying_attributes_update(self):
        # Test that the randomly-varying simulated attributes vary as expected

        self.maxDiff = None
        model = self.instance.model
        varying_attributes = sorted(self.varying_attributes)
        # Disable polling on the test attributes so that values are not cached by Tango
        disable_attributes_polling(
            self, self.tango_dp, self.instance, varying_attributes)

        # Mock the simulation quantities' next_val() call to ensure that the same value is
        # never returned twice, otherwise it is impossible to tell if a value really
        # changed
        for var, quant in list(model.sim_quantities.items()):
            if var in varying_attributes:
                unique_next_val = never_repeat(quant.next_val)
                patcher = mock.patch.object(quant, 'next_val')
                mock_next_val = patcher.start()
                self.addCleanup(patcher.stop)
                mock_next_val.side_effect = unique_next_val

        ## Test that quantities change after more some time
        # Set update time quite short
        update_period = 0.01
        model.min_update_period = update_period
        # Sleep long enough to ensure an update post mocking
        time.sleep(update_period*1.05)
        # Ensure that always_executed_hook() is called
        self.tango_dp.State()
        # Get initial values
        LOGGER.debug('Getting init values')
        initial_vals = read_attributes_as_dicts(self.tango_dp, varying_attributes)
        LOGGER.debug('Sleeping')
        time.sleep(1.05*update_period)
        # Ensure that always_executed_hook() is called
        self.tango_dp.State()
        LOGGER.debug('Getting updated values')
        updated_vals = read_attributes_as_dicts(self.tango_dp, varying_attributes)

        # 1) check that the value of *each* attribute has changed
        # 2) check that the difference in timestamp is more than update_period
        for attr_name, initial_attr in list(initial_vals.items()):
            updated_attr = updated_vals[attr_name]
            self.assertNotEqual(updated_attr['value'], initial_attr['value'],
                                "attribute {!r} unchanged after update".format(attr_name))
            dt = updated_attr['time'] - initial_attr['time']
            self.assertGreaterEqual(dt, update_period)
