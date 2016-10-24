import unittest
import logging
import weakref
import time
import operator
import sys
import mock

from functools import wraps
from collections import defaultdict

from PyTango import server as TS
from PyTango import AttrQuality
from PyTango import DevState

from devicetest import TangoTestContext
from katcp.testutils import start_thread_with_cleanup
from katcore.testutils import cleanup_tempfile

from mkat_tango.testutils import set_attributes_polling, ClassCleanupUnittestMixin

from mkat_tango.translators import tango_inspecting_client

LOGGER = logging.getLogger(__name__)

def _test_attr(attr_dummy_fn):
    """Decorator for a :class:`PyTango.server.Device` test attribute

    Allows an empty reading function. Attribute values are instead read from the
    device instance's `attr_return_vals` dict.

    Example
    =======

    class TangoTestDevice(PyTango.server.Device):
        __metaclass__ = PyTango.server..DeviceMeta

        def init_device(self):
            super(TangoTestDevice, self).init_device()
            self.attr_return_vals = dict(
                blah=(123.456, time.time(), PyTango.AttrQuality.ATTR_VALID))

        @PyTango.Server.attribute(dtype=float)
        @_test_attr
        def blah(self): pass

    This will set up a read function for the `blah` attribute that reads the
    (value, timestamp, attribute quality) tuple from
    `self.attr_return_vals['blah']`. If the timestamp value is None,
    `self.attr_time()` is called to get the timestamp. `self.attr_time` is
    initialised to time.time()

    """
    attr_name = attr_dummy_fn.__name__

    @wraps(attr_dummy_fn)
    def attr_fn(self):
        val, ts, qual = self.attr_return_vals[attr_name]
        if ts is None:
            ts = self.attr_time()
        if self.log_attribute_reads:
            LOGGER.debug('Attr {!r} returning {!r}'.format(
                attr_name, (val, ts, qual)) )
        return val, ts, qual

    return attr_fn


class TangoTestDevice(TS.Device):
    __metaclass__ = TS.DeviceMeta
    instances = weakref.WeakValueDictionary() # Access instances for debugging
    # Can be mocked to control timestamps returned by attributes
    attr_time = time.time
    log_attribute_reads = False

    def init_device(self):
        super(TangoTestDevice, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        self.set_state(DevState.ON)
        # Return values for attributes as (val, timestamp, attr_quality). If
        # timestamp is None, self.attr_time is called to get the time
        self.attr_return_vals = dict(
            ScalarBool=(True, None, AttrQuality.ATTR_VALID),
            ScalarDevUChar=(ord('a'), None, AttrQuality.ATTR_VALID),
            ScalarDevLong=(1234567890, None, AttrQuality.ATTR_VALID),
            ScalarDevDouble=(3.1415, None, AttrQuality.ATTR_VALID),
            ScalarDevString=('The quick brown fox.', None, AttrQuality.ATTR_VALID),
            ScalarDevEncoded=(('enc', bytearray([10, 20, 30, 15])),
                              None, AttrQuality.ATTR_VALID),
            )
        self.static_attributes = tuple(sorted(self.attr_return_vals.keys()))

    @TS.attribute(dtype='DevBoolean',
                  doc='An example scalar boolean attribute', polling_period=1000,
                  event_period=25)
    @_test_attr
    def ScalarBool(self): pass

    @TS.attribute(dtype='DevUChar', doc='An example scalar UChar attribute',
                  polling_period=1000, event_period=25)
    @_test_attr
    def ScalarDevUChar(self): pass

    @TS.attribute(dtype='DevLong', doc='An example scalar Long attribute',
                  polling_period=1000, event_period=25)
    @_test_attr
    def ScalarDevLong(self): pass

    @TS.attribute(dtype='DevDouble', doc='An example scalar Double attribute',
                  polling_period=1000, event_period=25)
    @_test_attr
    def ScalarDevDouble(self): pass

    @TS.attribute(dtype='DevString', doc='An example scalar String attribute',
                  polling_period=1000, event_period=25)
    @_test_attr
    def ScalarDevString(self): pass

    @TS.attribute(dtype='DevEncoded', doc='An example scalar Encoded attribute',
                  polling_period=1000, event_period=25)
    @_test_attr
    def ScalarDevEncoded(self): pass

    static_commands = ('ReverseString', 'MultiplyInts', 'Void',
                       'MultiplyDoubleBy3')
    # Commands that come from the Tango library
    standard_commands = ('Init', 'State', 'Status')


    ReverseString_command_kwargs = dict(
        doc_in='A string to reverse',
        dtype_in='DevString',
        doc_out='The reversed string',
        dtype_out='DevString')
    @TS.command(**ReverseString_command_kwargs)
    def ReverseString(self, in_str):
        """A scalar string -> scalar string command"""
        return in_str[::-1]

    MultiplyInts_command_kwargs = dict(
        doc_in='Array of integers to add',
        dtype_in='DevVarLong64Array',
        doc_out='Sum of input integer array',
        dtype_out='DevLong64')
    @TS.command(**MultiplyInts_command_kwargs)
    def MultiplyInts(self, in_ints):
        return reduce(operator.mul, in_ints)

    # Need empty dict for tests to work
    Void_command_kwargs = {}
    @TS.command(**Void_command_kwargs)
    def Void(self):
        pass

    MultiplyDoubleBy3_command_kwargs = dict(
        doc_in='A Double to multiply by 3',
        dtype_in='DevDouble',
        doc_out='Input multiplied by 3',
        dtype_out='DevDouble')
    @TS.command(**MultiplyDoubleBy3_command_kwargs)
    def MultiplyDoubleBy3(self, a_double):
        return a_double * 3.0

    # the State command is implemented by the tango library, but include the
    # information structure so that tests can use it to compare docstrings, etc.
    State_command_kwargs = dict(
        doc_in='Void',
        dtype_in='DevVoid',
        doc_out='Device state',
        dtype_out='DevState')

# DevVoid, DevBoolean, DevUChar, DevShort, DevUShort, DevLong, DevULong, DevLong64,
# DevULong64, DevDouble, DevString, DevEncoded, DevVarBooleanArray,
# DevVarCharArray, DevVarShortArray, DevVarLongArray, DevVarLong64Array,
# DevVarULong64Array, DevVarFloatArray, DevVarDoubleArray, DevVarUShortArray,
# DevVarULongArray, DevVarStringArray, DevVarLongStringArray, DevVarDoubleStringArray


class TangoSetUpClass(ClassCleanupUnittestMixin, unittest.TestCase):
    longMessage=True

    @classmethod
    def setUpClassWithCleanup(cls):
        """Do class-level setup  and ensure that cleanup functions are called

        In this method calls to `cls.addCleanup` is forwarded to
        `cls.addCleanupClass`, which means callables registered with
        `cls.addCleanup()` is added to the class-level cleanup function stack.

        """
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.tango_context = TangoTestContext(
            TangoTestDevice, db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)
        cls.tango_dp = cls.tango_context.device
        cls.tango_ds = cls.tango_context.server
        cls.test_device = TangoTestDevice.instances[cls.tango_dp.name()]
        cls.test_device.log_attribute_reads = True
        cls.DUT = tango_inspecting_client.TangoInspectingClient(cls.tango_dp)


class test_TangoInspectingClient(TangoSetUpClass):

    def _test_attributes(self, attributes_data):
        # Check that the standard Tango sensors are there
        self.assertIn('State', attributes_data)
        self.assertIn('Status', attributes_data)
        # Now remove them from the data since we don't have test data for them
        del attributes_data['State']
        del attributes_data['Status']

        # Test that all our test device attributes are present
        self.assertEqual(tuple(sorted(attributes_data.keys())),
                         self.test_device.static_attributes)
        # And check some of their data
        for attr_name, attr_data in attributes_data.items():
            td_props = getattr(
                self.test_device, attr_name).get_properties()
            self.assertEqual(attr_data.description, td_props.description)

    def test_inspect_attributes(self):
        attributes_data = self.DUT.inspect_attributes()
        self._test_attributes(attributes_data)

    def _test_commands(self, commands_data):
        # Check that the standard Tango commands are there
        for cmd in self.test_device.standard_commands:
            self.assertIn(cmd, commands_data)
        # Check that our static test commands are there
        for cmd in self.test_device.static_commands:
            self.assertIn(cmd, commands_data)
        # Check that there are no extra commands
        self.assertEqual(len(commands_data),
                         len(self.test_device.standard_commands) +
                         len(self.test_device.static_commands))

    def test_inspect_commands(self):
        commands_data = self.DUT.inspect_commands()
        self._test_commands(commands_data)

    def test_inspect(self):
        self.DUT.inspect()
        self._test_attributes(self.DUT.device_attributes)
        self._test_commands(self.DUT.device_commands)

    def test_setup_attribute_sampling(self):
        poll_period = 10000        # in milliseconds
        test_attributes = self.test_device.static_attributes
        set_attributes_polling(self, self.tango_dp, self.test_device,
                               {attr: poll_period
                                for attr in test_attributes})
        recorded_samples = {attr: [] for attr in test_attributes}
        self.DUT.inspect()
        with mock.patch.object(self.DUT, 'sample_event_callback') as sec:
            def side_effect(attr, *x):
                if attr in test_attributes:
                    recorded_samples[attr].append(x)
                    LOGGER.debug('Received {!r} for attr {!r}'.format(x, attr))
            sec.side_effect = side_effect
            self.addCleanup(self.DUT.clear_attribute_sampling)
            LOGGER.debug('Setting attribute sampling')
            self.DUT.setup_attribute_sampling()
            self.DUT.clear_attribute_sampling()

        # Check that the initial updates were received for each attribute for
        # at least the periodic event
        attr_event_type_events = {}
        for attr, events in recorded_samples.items():
            attr_event_type_events[attr] = defaultdict(list)
            for event in events:
                event_type = event[4]
                attr_event_type_events[attr][event_type].append(event)

        periodic_updates_per_attr = {
            attr: len(attr_event_type_events[attr]['periodic'])
            for attr in test_attributes}
        self.assertEqual(
            periodic_updates_per_attr,
            {attr: 1 for attr in test_attributes},
            "Exactly one periodic update not received for each test attribute.")


class test_TangoInspectingClientStandard(TangoSetUpClass):

    def test_tango_standard_attributes(self):
        standard_tango_attributes = ('State', 'Status',)
        is_polled = self.tango_dp.is_attribute_polled
        get_poll_period = self.tango_dp.get_attribute_poll_period

        # Confirm that polling is not set on the attributes
        for attr in standard_tango_attributes:
            self.assertEqual(is_polled(attr), False)

        recorded_samples = {attr: [] for attr in standard_tango_attributes}
        self.DUT.inspect()
        with mock.patch.object(self.DUT, 'sample_event_callback') as sec:
            def side_effect(attr, *x):
                if attr in standard_tango_attributes:
                    recorded_samples[attr].append(x)
                    LOGGER.debug('Received {!r} for attr {!r}'.format(x, attr))
            sec.side_effect = side_effect
            self.addCleanup(self.DUT.clear_attribute_sampling)
            LOGGER.debug('Setting attribute sampling')
            self.DUT.setup_attribute_sampling()

        # Confirm that polling is set to expected period of 1000 ms
        for attr in standard_tango_attributes:
            self.assertEqual(is_polled(attr), True)
            self.assertEqual(get_poll_period(attr), 1000)

        attr_event_type_events = {}
        for attr, events in recorded_samples.items():
            attr_event_type_events[attr] = defaultdict(list)
            for event in events:
                event_type = event[4]
                attr_event_type_events[attr][event_type].append(event)

        periodic_updates_per_attr = {
            attr: len(attr_event_type_events[attr]['periodic'])
            for attr in standard_tango_attributes}
        self.assertEqual(
            periodic_updates_per_attr,
            {attr: 1 for attr in standard_tango_attributes},
            "Exactly one periodic update not received for each test attribute.")

        self.DUT.clear_attribute_sampling()
    # NM 2016-04-13 TODO Test for when dynamic attributes are added/removed It seems this
    # is only implemented in tango 9, so we can't really do this properly till we
    # upgrade. https://sourceforge.net/p/tango-cs/feature-requests/90/?limit=25
