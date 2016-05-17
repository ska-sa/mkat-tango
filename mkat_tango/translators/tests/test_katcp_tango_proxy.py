import time
import mock
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
        self.katcp_address = self.DUT.katcp_server.bind_address
        self.host, self.port = self.katcp_address
        self.client = BlockingTestClient(self, self.host, self.port)
        start_thread_with_cleanup(self, self.client, start_timeout=1)

    def test_from_address(self):
        self.assertEqual(self.client.is_connected(), True)
        reply, informs = self.client.blocking_request(Message.request('watchdog'))
        self.assertTrue(reply.reply_ok(), True)

    def test_sensor_attribute_match(self):
        reply, informs = self.client.blocking_request(Message.request('sensor-list'))
        sensor_list = set([inform.arguments[0] for inform in informs])
        tango_device_proxy = self.DUT.inspecting_client.tango_dp
        attribute_list = set(tango_device_proxy.get_attribute_list())
        self.assertEqual(attribute_list, sensor_list,
            "\n\n!KATCP server sensor list differs from the TangoTestServer "
            "attribute list!\n\nThese sensors are"
            " missing:\n%s\n\nFound these unexpected attributes:\n%s"
            % ("\n".join(sorted([str(t) for t in sensor_list - attribute_list])),
               "\n".join(sorted([str(t) for t in attribute_list - sensor_list]))))

    def test_attribute_sensor_update(self):
        tango_dp = self.tango_context.device
        test_device = TangoTestDevice.instances[tango_dp.name()]
        poll_period = 1000
        sleep_time = (poll_period/1000.)*10
        katcp_server = self.DUT.katcp_server
        tic = self.DUT.inspecting_client
        sensors = []
        observers = {}
        for attr_name in tango_dp.get_attribute_list():
            if attr_name != 'ScalarDevEncoded' and attr_name != 'ScalarDevUChar':
                # Attaching a observers onto the katcp sensors to allowing
                # logging of updates into a dictionary with list values.
                observers[attr_name] = observer = SensorObserver()
                katcp_server.get_sensor(attr_name).attach(observer)
                sensors.append(attr_name)
            else:
                LOGGER.debug('Found unexpected attributes')
        testutils.set_attributes_polling(self, tango_dp, test_device,
                         {attr: poll_period
                          for attr in tango_dp.get_attribute_list()})
        self.addCleanup(tic.clear_attribute_sampling)
        LOGGER.debug('Setting attribute sampling')
        tic.setup_attribute_sampling(periodic=False)
        self.addCleanup(tic.clear_attribute_sampling)
        # Waiting for the specified number (5) of polling periods 
        time.sleep(sleep_time)
        tic.clear_attribute_sampling()
        for sensor in sensors:
            obs = observers[sensor]
            self.assertAlmostEqual(len(obs.updates), 10, delta=3)
            katcp_server.get_sensor(attr_name).detach(obs)

class SensorObserver(object):
   def __init__(self):
       self.updates = []

   def update(self, sensor, *reading):
       self.updates.append((sensor, reading))
       LOGGER.debug('Received {!r} for attr {!r}'.format(sensor, reading))
