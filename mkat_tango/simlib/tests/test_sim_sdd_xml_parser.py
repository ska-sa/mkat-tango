import time
import mock
import logging
import unittest

import pkg_resources

from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from mkat_tango.simlib import sim_sdd_xml_parser
from mkat_tango.testutils import ClassCleanupUnittestMixin

import PyTango

LOGGER = logging.getLogger(__name__)

expected_mandatory_monitoring_point_parameters = frozenset([
    "description", "data_type",
    "Size", "writable", "min_value", "max_value",
    "SamplingFrequency", "LoggingLevel"])

expected_mandatory_cmd_parameters = frozenset([
    "cmd_id", "cmd_name", "cmd_description", "cmd_type",
    "time_out", "max_retry", "time_for_exec", "available_modes",
    "cmd_params", "response_list"])


# The desired information for the atttribute pressure when the weather_sim xmi file is
# parsed by the Xmi_Parser.
expected_pressure_attr_info = {
        'data_type': 'float',
        'description': None,
        'max_value': '1100',
        'min_value': '500',
        'Size': '0',
        'writable': None,
        'PossibleValues': None,
        'SamplingFrequency': {
            'DefaultValue': None,
            'MaxValue': None
        },
        'LoggingLevel': None
}
# The desired information for the 'On' command when the weather_sim xmi file is parsed
expected_on_cmd_info = {
        'cmd_name': 'ON',
        'cmd_description': None,
        'cmd_id': None,
        'cmd_type': None,
        'time_out': None,
        'max_retry': None,
        'available_modes': {},
        'cmd_params': None,
        'response_list': {
            'msg': {
                'ParameterName': 'msg',
                'ParameterID': None,
                'ParameterValue': None
            },
            'gsm': {
                'ParamaterName': 'gsm',
                'ParameterID': None,
                'ParameterValue': None
            }
        }
}

class GenericSetup(unittest.TestCase):
    longMessage = True

    def setUp(self):
        super(GenericSetup, self).setUp()
        self.xml_file = pkg_resources.resource_filename('mkat_tango.simlib.tests',
                                                'WeatherSimulator_CN.xml')
        self.xml_parser = sim_sdd_xml_parser.SDD_Parser()
        self.xml_parser.parse(self.xml_file)

class test_XmiParser(GenericSetup):
    def test_parsed_attributes(self):
        """Testing that the attribute information parsed matches with the one captured
        in the XMI file.
        """
        actual_parsed_attrs = self.xml_parser.get_reformatted_device_attr_metadata()
        expected_attr_list = ['Insolation', 'Temperature', 'Pressure', 'Rainfall',
                              'Relative_Humidity', 'Wind_Direction', 'Wind_Speed']
        actual_parsed_attr_list = actual_parsed_attrs.keys()
        self.assertGreater(len(actual_parsed_attr_list), 0,
                "There is no attribute information parsed")
        self.assertEquals(set(expected_attr_list), set(actual_parsed_attr_list),
                 'There are missing attributes')

        # Test if all the parsed attributes have the mandatory properties
        for attr_name, attribute_metadata in actual_parsed_attrs.items():
            for param in expected_mandatory_monitoring_point_parameters:
                self.assertIn(param, attribute_metadata.keys(),
                        "The parsed attribute '%s' does not the mandotory parameter "
                        "'%s' " % (attr_name, param))

        # Using the made up pressure attribute expected results as we haven't generated
        # the full test data for the other attributes.
        self.assertIn('Pressure', actual_parsed_attrs.keys(),
                "The attribute pressure is not in the parsed attribute list")
        actual_parsed_pressure_attr_info = actual_parsed_attrs['Pressure']

        # Compare the values of the attribute properties captured in the POGO generated
        # xmi file and the ones in the parsed attribute data structure.
        for prop in expected_pressure_attr_info:
            self.assertEquals(actual_parsed_pressure_attr_info[prop],
                    expected_pressure_attr_info[prop],
                    "The expected value for the parameter '%s' does not match "
                    "with the actual value" % (prop))


class test_PopModelQuantities(GenericSetup):

    def test_model_populator(self):
        """Testing that the model quantities that are added to the model match with
        the attributes specified in the XMI file.
        """
        device_name = 'tango/device/instance'
        pmq = sim_sdd_xml_parser.PopulateModelQuantities(self.xml_parser, device_name)

        self.assertEqual(device_name, pmq.sim_model.name,
                "The device name and the model name do not match.")
        expected_quantities_list = ['Insolation', 'Temperature', 'Pressure', 'Rainfall',
                                    'Relative_Humidity', 'Wind_Direction',
                                    'Wind_Speed']
        actual_quantities_list = pmq.sim_model.sim_quantities.keys()
        self.assertEqual(set(expected_quantities_list), set(actual_quantities_list),
                "The are quantities missing in the model")
