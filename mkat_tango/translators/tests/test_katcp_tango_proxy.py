import time
import logging

import devicetest

from devicetest import TangoTestContext
from katcp import Message
from katcp.testutils import start_thread_with_cleanup, BlockingTestClient
from katcore.testutils import cleanup_tempfile

from mkat_tango.translators.tests.test_tango_inspecting_client import (
    TangoTestDevice, ClassCleanupUnittest)

from mkat_tango import testutils
from mkat_tango.translators import katcp_tango_proxy

LOGGER = logging.getLogger(__name__)

class test_TangoDevice2KatcpProxy(ClassCleanupUnittest):

    DUT = None

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.tango_context = TangoTestContext(TangoTestDevice, db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)
        cls.tango_device_address = cls.tango_context.get_device_access()
        devicetest.Patcher.unpatch_device_proxy()

    def setUp(self):
        self.DUT = katcp_tango_proxy.TangoDevice2KatcpProxy.from_addresses(
            ("", 0), self.tango_device_address)
        start_thread_with_cleanup(self, self.DUT, start_timeout=1)
        self.katcp_server = self.DUT.katcp_server
        self.tango_device_proxy = self.tango_context.device
        self.tango_test_device = TangoTestDevice.instances[self.tango_device_proxy.name()]
        self.katcp_address = self.katcp_server.bind_address
        self.host, self.port = self.katcp_address
        self.client = BlockingTestClient(self, self.host, self.port)
        start_thread_with_cleanup(self, self.client, start_timeout=1)
        self.client.wait_protocol(timeout=1)

    def test_from_address(self):
        self.assertEqual(self.client.is_connected(), True)
        reply, informs = self.client.blocking_request(Message.request('watchdog'))
        self.assertTrue(reply.reply_ok(), True)

    def test_sensor_attribute_match(self):
        reply, informs = self.client.blocking_request(Message.request('sensor-list'))
        sensor_list = set([inform.arguments[0] for inform in informs])
        attribute_list = set(self.tango_device_proxy.get_attribute_list())
        NOT_IMPLEMENTED_SENSORS = set(['ScalarDevEncoded'])
        self.assertEqual(attribute_list - NOT_IMPLEMENTED_SENSORS, sensor_list,
            "\n\n!KATCP server sensor list differs from the TangoTestServer "
            "attribute list!\n\nThese sensors are"
            " missing:\n%s\n\nFound these unexpected attributes:\n%s"
            % ("\n".join(sorted([str(t) for t in sensor_list - attribute_list])),
               "\n".join(sorted([str(t) for t in attribute_list - sensor_list]))))

    def test_initial_attribute_sensor_values(self):
        sensors = self.katcp_server.get_sensors()
        attributes = self.tango_test_device.attr_return_vals
        for sensor in sensors:
            sensor_value = sensor.value()
            if sensor.name in ['State', 'Status']:
                # This sensors are handled specially since they are tango library
                # Attributes with State returning a device state object
                if sensor.name in ['State']:
                    state = str(self.tango_device_proxy.state())
                    # PyTango._PyTango.DevState.ON is device state object
                    self.assertEqual(sensor_value, state)
                else:
                    status = self.tango_device_proxy.status()
                    self.assertEqual(sensor_value, status)
            else:
                attribute_value = attributes[sensor.name][0]
                self.assertEqual(sensor_value, attribute_value)

    def test_attribute_sensor_update(self):
        sensors = []
        observers = {}
        # when polling at a period of less than 50 ms, tango becomes
        # inconsistent with the updates generated  i.e. the observed
        # time difference between updates fluctuates (50+-20 ms)
        poll_period = 50
        num_periods = 10
        # sleep time is 10 poll periods plus a little
        sleep_time = poll_period/1000. * (num_periods + 0.5)
        testutils.set_attributes_polling(self, self.tango_device_proxy,
                           self.tango_test_device, {attr: poll_period
                           for attr in self.tango_device_proxy.get_attribute_list()})
        EXCLUDED_ATTRS = set([
                'State',    # Tango library attribute, Cannot change event_period
                'Status',   # Tango library attribute, Cannot change event_period
                'ScalarDevEncoded'   # Not implemented sensor, to be removed once
                # attribute type DevEncoded is handled as katcp server sensor types
                ])

        for attr_name in self.tango_device_proxy.get_attribute_list():
            if attr_name not in EXCLUDED_ATTRS:
                # Instantiating observers and attaching them onto the katcp
                # sensors to allow logging of periodic event updates into a list
                observers[attr_name] = observer = SensorObserver()
                self.katcp_server.get_sensor(attr_name).attach(observer)
                sensors.append(attr_name)
            else:
                LOGGER.debug('Found unexpected attributes')
        time.sleep(sleep_time)

        for sensor in sensors:
            self.katcp_server.get_sensor(sensor).detach(observer)
            obs = observers[sensor]
            self.assertAlmostEqual(len(obs.updates), num_periods, delta=2)

class SensorObserver(object):
    def __init__(self):
        self.updates = []

    def update(self, sensor, reading):
        self.updates.append((sensor, reading))
        LOGGER.debug('Received {!r} for attr {!r}'.format(sensor, reading))
