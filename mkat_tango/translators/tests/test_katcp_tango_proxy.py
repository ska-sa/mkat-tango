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
