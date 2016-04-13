import unittest
import logging
import weakref
import time

from functools import wraps

from PyTango import server as TS
from PyTango import AttrQuality

from devicetest import TangoTestContext
from katcp.testutils import start_thread_with_cleanup
from katcore.testutils import cleanup_tempfile

from mkat_tango.translators import tango_inspecting_client

LOGGER = logging.getLogger(__name__)

def _test_attr(attr_dummy_fn):
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
        # Return values for attributes as (val, timestamp, attr_quality). If timestamp is
        # None, self.attr_time is called to get the time
        self.attr_return_vals = dict(
            ScalarBool=(True, None, AttrQuality.ATTR_VALID),
            ScalarDevUChar=('a', None, AttrQuality.ATTR_VALID),
            ScalarDevLong=(1234567890, None, AttrQuality.ATTR_VALID),
            ScalarDevDouble=(3.1415, None, AttrQuality.ATTR_VALID),
            ScalarDevString=('The quick brown fox.', None, AttrQuality.ATTR_VALID),
            ScalarDevEncoded=(('enc', bytearray([10, 20, 30, 15])),
                              None, AttrQuality.ATTR_VALID),
            )
        self.static_attributes = sorted(
            self.attr_return_vals.keys() + ['State', 'Status'])


    @TS.attribute(dtype='DevBoolean',
                  doc='An example scalar boolean attribute')
    @_test_attr
    def ScalarBool(self): pass

    @TS.attribute(dtype='DevUChar', doc='An example scalar UChar attribute')
    @_test_attr
    def ScalarDevUChar(self): pass

    @TS.attribute(dtype='DevLong', doc='An example scalar Long attribute')
    @_test_attr
    def ScalarDevLong(self): pass

    @TS.attribute(dtype='DevDouble', doc='An example scalar Double attribute')
    @_test_attr
    def ScalarDevDouble(self): pass

    @TS.attribute(dtype='DevString', doc='An example scalar String attribute')
    @_test_attr
    def ScalarDevString(self): pass

    @TS.attribute(dtype='DevEncoded', doc='An example scalar Encoded attribute')
    @_test_attr
    def ScalarDevEncoded(self): pass


# DevVoid, DevBoolean, DevUChar, DevShort, DevUShort, DevLong, DevULong, DevLong64,
# DevULong64, DevDouble, DevString, DevEncoded, DevVarBooleanArray,
# DevVarCharArray, DevVarShortArray, DevVarLongArray, DevVarLong64Array,
# DevVarULong64Array, DevVarFloatArray, DevVarDoubleArray, DevVarUShortArray,
# DevVarULongArray, DevVarStringArray, DevVarLongStringArray, DevVarDoubleStringArray


class test_TangoInspectingClient(unittest.TestCase):
    def setUp(self):
        self.tango_db = cleanup_tempfile(self, prefix='tango', suffix='.db')
        self.tango_context = TangoTestContext(
            TangoTestDevice, db=self.tango_db)
        start_thread_with_cleanup(self, self.tango_context)
        self.tango_dp = self.tango_context.device
        self.tango_ds = self.tango_context.server
        self.test_device = TangoTestDevice.instances[self.tango_dp.name()]
        self.test_device.log_attribute_reads = True
        self.DUT = tango_inspecting_client.TangoInspectingClient(self.tango_dp)

    def test_inspect_attributes(self):
        attributes_data = self.DUT.inspect_attributes()
        import IPython ; IPython.embed()

        self.assertEqual(sorted(attributes_data.keys()),
                         self.test_device.static_attributes)
        for attr_name, attr_data in attributes_data.items():
            td_props = getattr(
                self.test_device, attr_name).get_attribute_config()
            self.assertEqual(attr_data.description, td_props.description)


    # TODO Test for when dynamic attributes are added/removed
