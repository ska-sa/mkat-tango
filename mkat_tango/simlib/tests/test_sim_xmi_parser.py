import time
import mock
import logging
import unittest
import random

import pkg_resources

from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from mkat_tango.simlib import sim_xmi_parser
from mkat_tango.testutils import ClassCleanupUnittestMixin

import PyTango

LOGGER = logging.getLogger(__name__)

default_pogo_commands = ['State', 'Status']

expected_mandatory_attr_parameters = frozenset([
    "max_dim_x", "max_dim_y", "data_format", "period",
    "data_type", "writable", "name", "description", "delta_val",
    "max_alarm", "max_value", "min_value", "standard_unit", "min_alarm",
    "max_warning", "unit", "display_unit","format", "delta_t", "label",
    "min_warning"])

expected_mandatory_cmd_parameters = frozenset([
    "name", "arginDescription", "arginType", "argoutDescription", "argoutType",
    "description", "displayLevel", "polledPeriod", "execMethod"])

expected_mandatory_default_cmds = [
    {
        "name": 'State',
        "arginDescription": 'none',
        "arginType": PyTango._PyTango.CmdArgType.DevVoid,
        "argoutDescription": 'Device state',
        "argoutType": PyTango.utils.DevState,
        "description": 'This command gets the device state (stored in its '
            'device_state data member) and returns it to the caller.',
        "displayLevel": 'OPERATOR',
        "polledPeriod": '0',
        "execMethod": 'dev_state',
    },
    {
        "arginDescription": 'none',
        "arginType": PyTango._PyTango.CmdArgType.DevVoid,
        "argoutDescription": 'Device status',
        "argoutType": PyTango._PyTango.CmdArgType.DevString,
        "description": 'This command gets the device status'
            '(stored in its device_status data member) and returns it to the caller.',
        "displayLevel": 'OPERATOR',
        "execMethod": 'dev_status',
        "name": 'Status',
        "polledPeriod": '0',
     }
]

pressure_attr_info = {
        'name': 'pressure',
        'data_type': PyTango.CmdArgType.DevDouble,
        'period': '1000',
        'writable': 'READ',
        'description': 'Barometric pressure in central telescope area.',
        'label': 'Barometric pressure',
        'unit': 'mbar',
        'standard_unit': '',
        'display_unit': '',
        'format': '',
        'max_value': '1100',
        'min_value': '500',
        'max_alarm': '1000',
        'min_alarm': '',
        'max_warning': '900',
        'min_warning': '',
        'delta_t': '',
        'delta_val': '',
        'data_format': PyTango.AttrDataFormat.SCALAR,
        'max_dim_y': 0,
        'max_dim_x': 1,
        'abs_change': '0.5',
        'rel_change': '10',
        'event_period': '1000',
        'archive_abs_change': '0.5',
        'archive_period': '1000',
        'archive_rel_change': '10'}

on_cmd_info = {
        'name': 'On',
        'description': 'Turn On Device',
        'execMethod': 'on',
        'displayLevel': 'OPERATOR',
        'polledPeriod': '0',
        'isDynamic': 'false',
        'arginDescription': '',
        'arginType': PyTango.CmdArgType.DevVoid,
        'argoutDescription': 'ok | Device ON',
        'argoutType': PyTango.CmdArgType.DevString}


class test_SimXmiParser(ClassCleanupUnittestMixin, unittest.TestCase):
    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.xmi_file = pkg_resources.resource_filename('mkat_tango.simlib.tests',
                                                        'weather_sim.xmi')
        # Since the sim_xmi_parser gets the xmi file from the device properties
        # in the tango database, here the method is mocked to return the xmi
        # file that found using the pkg_resources since it is included in the
        # test module
        with mock.patch(sim_xmi_parser.__name__+'.get_xmi_description_file_name'
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
        """ Testing whether the attributes specified in the POGO generated xmi file
        are added to the TANGO device
        """
        attributes = set(self.device.get_attribute_list())
        expected_attributes = []
        default_attributes = {'State', 'Status'}
        for attribute_data in self.xmi_parser.device_attributes:
            expected_attributes.append(attribute_data['dynamicAttributes']['name'])
        self.assertEqual(set(expected_attributes),  attributes - default_attributes,
                         "Actual tango device attribute list differs from expected list!")

    def test_attribute_properties(self):
        attribute_list = self.device.get_attribute_list()
        attribute_data = self.xmi_parser.get_reformatted_device_attr_metadata()

        for attr_name, attr_metadata in attribute_data.items():
            self.assertIn(attr_name, attribute_list,
                    "Device does not have the attribute %s" % (attr_name))
            attr_query_data = self.device.attribute_query(attr_name)

            for attr_parameter in attr_metadata:
                expected_attr_value = attr_metadata[attr_parameter]
                attr_prop_value = getattr(attr_query_data, attr_parameter, None)
                # Here the writable property is checked for, since Pogo
                # expresses in as a string (e.g. 'READ') where tango device return a
                # Pytango object `PyTango.AttrWriteType.READ` and taking
                # its string returns 'READ' which corresponds to the Pogo one.
                if attr_parameter in ['writable']:
                    attr_prop_value = str(attr_prop_value)

                if attr_prop_value == None:                 # None and 0 behaves the same way in an if statement.
                    # In the case where no attr_query data is not found it is
                    # further checked in the mentioned attribute object
                    # i.e. alarms and events
                    # (check `self._test_tango_property_object`)
                    attr_prop_value = self._get_attribute_property_object_value(
                            attr_query_data, attr_parameter)

                # Here the data_type property is checked for, since Pogo
                # expresses in as a PyTango object (e.g.`PyTango.DevDouble`)
                # where tango device return a corresponding int value (e.g. 5)
                # and taking int of `PyTango.DevDouble` returns 5.
                if attr_parameter in ['data_type']:
                    expected_attr_value = int(expected_attr_value)

                # For some reason tango device attribute properties not
                # stated are assigned a string 'Not Specified' or even 'No
                # writable Specified'
                if 'No' in str(attr_prop_value):
                    attr_prop_value = ''

                # Pogo doesn't seem to populate the format as expected i.e.
                # format = '', and tango  device return (e.g. %6.2f for
                # floating points)
                if attr_parameter in ['format']:
                    attr_prop_value = ''

                self.assertEqual(expected_attr_value, attr_prop_value,
                        "Non matching %s property for %s attribute" % (
                            attr_parameter, attr_name))

    def _get_attribute_property_object_value(self, attr_query_data, user_default_prop):
        """Extracting the tango attribute property value from alarms an events objects

        Parameters
        ----------
        attr_query_data : PyTango.AttributeInfoEx
            data structure containing string arguments of attribute properties
        user_default_prop : str
            user default property as per items in `POGO_USER_DEFAULT_ATTR_PROP_MAP`

        Returns
        -------
        attr_prop_value : str
            tango attribute property value

        Note
        ----
         `self.device.attribute_query(attr_name)` is
         a structure (inheriting from :class:`AttributeInfo`) containing
         available information for an attribute with the following members:
         - alarms : object containing alarm information (see AttributeAlarmInfo).
         - events : object containing event information (see AttributeEventInfo).
         Thus a sequence with desired attribute objects is defined and besides
         this object is the normal attribute properties, refere to
         POGO_USER_DEFAULT_ATTR_PROP_MAP keys dynamicAttributes and properties

        """
        tango_property_members = ['alarms', 'arch_event', 'ch_event', 'per_event']
        for member in tango_property_members:
            if member in ['alarms']:
                attr_prop_value = getattr(attr_query_data.alarms,
                                          user_default_prop, None)
            else:
                attr_prop_value = getattr(attr_query_data.events,
                                          member, None)
                # The per_event obect has attribute period
                # which is defferent from the object in the
                # POGO_USER_DEFAULT_ATTR_PROP_MAP (event_period)
                # used for # setting the value
                if 'period' in user_default_prop:
                    attr_prop_value = getattr(attr_prop_value,
                                              'period', None)
                else:
                    attr_prop_value = getattr(attr_prop_value,
                                              user_default_prop, None)
            if attr_prop_value:
                return attr_prop_value


class test_XMIParser(unittest.TestCase):
    longMessage = True

    def setUp(self):
        super(test_XMIParser, self).setUp()
        self.xmi_file = pkg_resources.resource_filename('mkat_tango.simlib.tests',
                                'weather_sim.xmi')
        with mock.patch(sim_xmi_parser.__name__+'.get_xmi_description_file_name'
                ) as mock_get_xmi_description_file_name:
             mock_get_xmi_description_file_name.return_value = self.xmi_file

        self.xmi_parser = sim_xmi_parser.Xmi_Parser(self.xmi_file)

    def test_object_instantiation(self):
        with self.assertRaises(TypeError):
            sim_xmi_parser.Xmi_Parser()
        self.assertEquals(True, hasattr(self.xmi_parser, 'device_attributes'),
            'The object has not device attribute list')
        self.assertEquals(True, hasattr(self.xmi_parser, 'device_commands'),
            'The object has no device command list')
        self.assertEquals(True, hasattr(self.xmi_parser, 'device_properties'),
                    'The object has no device properties list')

    def test_parsed_attributes(self):

        parsed_attrs = self.xmi_parser.get_reformatted_device_attr_metadata()
        expected_attr_list = ['insolation', 'temperature', 'pressure', 'rainfall',
                      'relativeHumidity', 'wind_direction', 'input_comms_ok',
                      'wind_speed']
        parsed_attr_list = parsed_attrs.keys()
        self.assertGreater(len(parsed_attr_list), 0, 
                "There is no attribute information parsed")
        self.assertEquals(set(expected_attr_list), set(parsed_attr_list),
                 'There are missing attributes')

        # Test if any one of the parsed attributes have all the mandatory parameter
        random_parsed_attr = random.choice(expected_attr_list)
        random_parsed_attr_info = parsed_attrs[random_parsed_attr]
        for param in expected_mandatory_attr_parameters:
            self.assertIn(param, random_parsed_attr_info.keys(),
                    "The parsed attribute '%s' does not the mandotory parameter "
                    "'%s' " % (random_parsed_attr, param))
        # Pick one attribute and test if its property information
        # has been parsed correctly.

        parsed_pressure_attr_info = parsed_attrs['pressure']

        # Compare the values of the attribute properties captured in the POGO generated
        # xmi file and the ones in the parsed attribute data structure.
        for prop in parsed_pressure_attr_info:
            self.assertEquals(parsed_pressure_attr_info[prop], pressure_attr_info[prop],
                    "The expected value for the parameter '%s' does not match "
                    "with the actual value" % (prop))

    def test_parsed_commands(self):

        parsed_cmds = self.xmi_parser.get_reformatted_cmd_metadata()
        expected_cmd_list = ['On', 'Off'] + default_pogo_commands
        parsed_cmd_list = parsed_cmds.keys()
        self.assertGreater(len(parsed_cmd_list), len(default_pogo_commands),
                "There are missing commands in the parsed list")
        self.assertEquals(set(expected_cmd_list), set(parsed_cmd_list),
                'There are some missing commands')

        # Test if any one of the parsed commands have all the mandatory parameter
        random_parsed_cmd = random.choice(expected_cmd_list)
        random_parsed_cmd_info = parsed_cmds[random_parsed_cmd]

        for param in expected_mandatory_cmd_parameters:
            self.assertIn(param, random_parsed_cmd_info.keys(),
                    "The parsed attribute '%s' does not the mandotory parameter "
                    "'%s' " % (random_parsed_cmd, param))

        # Pick one command (not a default command) and test if its property information "
        # has been parsed correctly"
        self.assertIn('On', parsed_cmds.keys(),
                "The 'On' command is not in the parsed command list")
        cmd_on_info = parsed_cmds['On']
        for prop in cmd_on_info:
            self.assertEqual(cmd_on_info[prop], on_cmd_info[prop],
                "The expected value for the command paramater '%s' "
                "does not match with the actual value" % (prop))

    def test_parsed_device_properties(self):
        #TODO (KM)
        pass


    def test_model_populator(self):

        device_name = 'tango/device/instance'
        with self.assertRaises(sim_xmi_parser.SimModelException):
            sim_xmi_parser.PopulateModelQuantities(self.xmi_file, device_name,
                    sim_model='some_model')
        pmq = sim_xmi_parser.PopulateModelQuantities(self.xmi_file, device_name)

        self.assertEqual(device_name, pmq.sim_model.name,
                "The device name and the model name do not match.")
        expected_quantities_list = ['insolation', 'temperature', 'pressure', 'rainfall',
                        'relativeHumidity', 'wind_direction', 'input_comms_ok',
                        'wind_speed']
        actual_quantities_list = pmq.sim_model.sim_quantities.keys()
        self.assertEqual(set(expected_quantities_list), set(actual_quantities_list),
                "The are quantities missing in the model")
