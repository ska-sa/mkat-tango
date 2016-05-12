import time
import logging

import devicetest

from devicetest import TangoTestContext
from katcp.testutils import start_thread_with_cleanup
from katcore.testutils import cleanup_tempfile

from mkat_tango.translators.tests.test_tango_inspecting_client import (
    TangoTestDevice, ClassCleanupUnittest)

from mkat_tango.translators import katcp_tango_proxy

LOGGER = logging.getLogger(__name__)


class test_TangoDevice2KatcpProxy(ClassCleanupUnittest):

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.tango_context = TangoTestContext(TangoTestDevice, db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)
        cls.tango_device_address = cls.tango_context.get_device_access()
        devicetest.Patcher.unpatch_device_proxy()


    def test_from_address(self):
        DUT = katcp_tango_proxy.TangoDevice2KatcpProxy.from_addresses(
            ("", 0), self.tango_device_address)
        print self.tango_context.get_device_access()
        start_thread_with_cleanup(self, DUT, start_timeout=1)
        katcp_address = DUT.katcp_server.bind_address
        print katcp_address
        # import IPython ; IPython.embed()
