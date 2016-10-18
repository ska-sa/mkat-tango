import time
import mock
import logging
import unittest

import pkg_resources

from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from mkat_tango.simlib import sim_xmi_parser
from mkat_tango.translators.tests.test_tango_inspecting_client import (
                ClassCleanupUnittestMixin)

LOGGER = logging.getLogger(__name__)

default_attributes = {'State', 'Status'}


class test_SimXmiParser(ClassCleanupUnittestMixin, unittest.TestCase):
    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.xmi_file = pkg_resources.resource_filename('mkat_tango.simlib.tests',
                                                        'weather_sim.xmi')
        with mock.patch('mkat_tango.simlib.sim_xmi_parser.get_xmi_description_file_name'
                                         ) as mock_get_xmi_description_file_name:
            mock_get_xmi_description_file_name.return_value = cls.xmi_file
            cls.properties = dict(sim_xmi_description_file=cls.xmi_file)
            cls.TangoDeviceServer = sim_xmi_parser.TangoDeviceServer
            cls.tango_context = TangoTestContext(cls.TangoDeviceServer, db=cls.tango_db,
                                                 properties=cls.properties)
            start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_SimXmiParser, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]
        self.xmi_parser = sim_xmi_parser.Xmi_Parser(self.xmi_file)

    def test_attribute_list(self):
        attributes = set(self.device.get_attribute_list())
        expected_attributes = []
        for attribute_data in self.xmi_parser.device_attributes:
            expected_attributes.append(attribute_data['name'])
        self.assertEqual(attributes - default_attributes, set(expected_attributes),
                         "Actual sensor list differs from expected list!")
