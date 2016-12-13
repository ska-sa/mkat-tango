import time
import mock
import unittest
import logging

import PyTango
import pkg_resources


from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from mkat_tango.simlib import simdd_json_parser
from mkat_tango.simlib import sim_xmi_parser
from mkat_tango.testutils import ClassCleanupUnittestMixin


MODULE_LOGGER = logging.getLogger(__name__)

# Mandotary parameters required to create a well configure Tango attribute.
expected_mandatory_attr_parameters = frozenset([
    "max_dim_x", "max_dim_y", "data_format", "period",
    "data_type", "writable", "name", "description", "delta_val",
    "max_alarm", "max_value", "min_value", "max_warning", "min_warning",
    "min_alarm", "unit", "delta_t", "label", "format"])

# Mandotary parameters required to create a well configure Tango command.
expected_mandatory_cmd_parameters = frozenset([
        'dformat_in', 'dformat_out', 'doc_in',
        'doc_out', 'dtype_in', 'dtype_out', 'name', ])

# The desired information for the atttribute pressure when the weather_SIMDD
# json file is parsed by the Simdd_Parser.
expected_temperature_attr_info = {
        'abs_change': '0.5',
        'archive_abs_change': '0.5',
        'archive_period': '1000',
        'archive_rel_change': '10',
        'data_format': '',
        'data_type': PyTango._PyTango.CmdArgType.DevDouble,
        'format': '6.2f',
        'delta_t': '1000',
        'delta_val': '0.5',
        'description': 'Current temperature outside near the telescope.',
        'display_level': 'OPERATOR',
        'event_period': '1000',
        'label': 'Outside Temperature',
        'max_alarm': '50',
        'max_bound': '50',
        'max_dim_x': '1',
        'max_dim_y': '0',
        'max_slew_rate': '1',
        'max_value': '51',
        'mean': '25',
        'min_alarm': '-9',
        'min_bound': '-10',
        'min_value': '-10',
        "min_warning": "-8",
        "max_warning": "49",
        'name': 'temperature',
        'period': '1000',
        'rel_change': '10',
        'unit': 'Degrees Centrigrade',
        'update_period': '1',
        'writable': 'READ'
    }

# The desired information for the On command when the weather_SIMDD
# json file is parsed by the Simdd_Parser.
expected_on_cmd_info = {
        'description': 'Turns On Device',
        'dformat_in': '',
        'dformat_out': '',
        'doc_in': 'No input parameter',
        'doc_out': 'Command responds',
        'dtype_in': 'Void',
        'dtype_out': 'String',
        'name': 'On'
    }


class GenericSetup(unittest.TestCase):
        longMessage = True

        def setUp(self):
            super(GenericSetup, self).setUp()
            self.simdd_json_file = pkg_resources.resource_filename(
                    'mkat_tango.simlib.tests', 'weather_SIMDD.json')
            self.simdd_parser = simdd_json_parser.Simdd_Parser(self.simdd_json_file)

class test_Simdd_Json_Parser(GenericSetup):
    def test_parsed_attributes(self):
        """Testing that the attribute information parsed matches with the one captured
        in the SIMDD json file.
        """
        actual_parsed_attrs = self.simdd_parser.get_reformatted_device_attr_metadata()
        expected_attr_list = ['insolation', 'temperature', 'pressure',
                              'rainfall', 'relative_humidity', 'wind_direction',
                              'wind_speed', 'input_comms_ok']
        actual_parsed_attr_list = actual_parsed_attrs.keys()
        self.assertGreater(
            len(actual_parsed_attr_list), 0, "There is no attribute information parsed")
        self.assertEquals(set(expected_attr_list), set(actual_parsed_attr_list),
                          'There are missing attributes')

        # Test if all the parsed attributes have the mandatory properties
        for attr_name, attribute_metadata in actual_parsed_attrs.items():
            for param in expected_mandatory_attr_parameters:
                self.assertIn(
                    param, attribute_metadata.keys(),
                    "The parsed attribute '%s' does not the mandotory parameter "
                    "'%s' " % (attr_name, param))

        # Using the made up temperature attribute expected results as we
        # haven't generated the full test data for the other attributes.
        self.assertIn('temperature', actual_parsed_attrs.keys(),
                      "The attribute pressure is not in the parsed attribute list")
        actual_parsed_pressure_attr_info = actual_parsed_attrs['temperature']

        # Compare the values of the attribute properties captured in the POGO
        # generated xmi file and the ones in the parsed attribute data structure.
        for prop in expected_temperature_attr_info:
            self.assertEquals(actual_parsed_pressure_attr_info[prop],
                              expected_temperature_attr_info[prop],
                              "The expected value for the parameter '%s' does "
                              "not match with the actual value" % (prop))


class test_PopModelQuantities(GenericSetup):

    def test_model_quantities(self):
        """Testing that the model quantities that are added to the model match with
        the attributes specified in the XMI file.
        """
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)

        self.assertEqual(device_name, pmq.sim_model.name,
                         "The device name and the model name do not match.")
        expected_quantities_list = ['insolation', 'temperature',
                                    'pressure', 'input_comms_ok',
                                    'rainfall', 'relative_humidity',
                                    'wind_direction', 'wind_speed']
        actual_quantities_list = pmq.sim_model.sim_quantities.keys()
        self.assertEqual(set(expected_quantities_list), set(actual_quantities_list),
                         "The are quantities missing in the model")

    def test_model_quantities_metadata(self):
        """Testing that the metadata of the quantities matches with the metadata
        data of the parsed attribute data captured in the SDD xml file.
        """
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)
        self.assertEqual(device_name, pmq.sim_model.name,
                         "The device name and the model name do not match.")
        attribute_metadata = self.simdd_parser.get_reformatted_device_attr_metadata()
        for sim_quantity_name, sim_quantity in (
                pmq.sim_model.sim_quantities.items()):
            sim_quantity_metadata = getattr(sim_quantity, 'meta')
            attr_meta = attribute_metadata[sim_quantity_name]
            for attr_param_name, attr_param_val in attr_meta.items():
                self.assertTrue(sim_quantity_metadata.has_key(attr_param_name),
                                "The param '%s' was not added to the model quantity"
                                " '%s'" % (attr_param_name, sim_quantity_name))
                self.assertEqual(
                    sim_quantity_metadata[attr_param_name], attr_param_val,
                    "The value of the param '%s' in the model quantity '%s' is "
                    "not the same with the one captured in the SDD xml file "
                    "for the monitoring point '%s'." % (
                        attr_param_name, sim_quantity_name, attr_param_name))

    def test_model_actions_overrides(self):
        """
        """
        device_name = 'tango/device/instance'
        pmq = sim_xmi_parser.PopulateModelQuantities(self.simdd_parser, device_name)
        model = pmq.sim_model
        cmd_info = self.simdd_parser.get_reformatted_cmd_metadata()
        sim_xmi_parser.PopulateModelActions(cmd_info, device_name, model)

        action_on = model.sim_actions['On']
        self.assertEqual(action_on(), "On returning")
