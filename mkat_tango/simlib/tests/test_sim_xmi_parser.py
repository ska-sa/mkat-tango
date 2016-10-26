import time
import mock
import logging
import unittest

import pkg_resources

from devicetest import TangoTestContext

from katcore.testutils import cleanup_tempfile
from katcp.testutils import start_thread_with_cleanup
from mkat_tango.simlib import sim_xmi_parser
from mkat_tango.testutils import ClassCleanupUnittestMixin

import PyTango

LOGGER = logging.getLogger(__name__)

default_attributes = {'State', 'Status'}

expected_attribute_data_structure = [{
    "attribute": {
        "displayLevel": '',
        "maxX": '',
        "maxY": '',
        "attType": '',
        "polledPeriod": '',
        "dataType": '',
        "isDynamic": '',
        "rwType": '',
        "allocReadMember": '',
        "name": ''
    },
    "eventCriteria": {
        "relChange": '',
        "absChange": '',
        "period": ''
    },
    "evArchiverCriteria": {
        "relChange": '',
        "absChange": '',
        "period": ''
    },
    "properties": {
        "description": '',
        "deltaValue": '',
        "maxAlarm": '',
        "maxValue": '',
        "minValue": '',
        "standardUnit": '',
        "minAlarm": '',
        "maxWarning": '',
        "unit": '',
        "displayUnit": '',
        "format": '',
        "deltaTime": '',
        "label": '',
        "minWarning": ''
    }
    }]

expected_mandatory_attr_parameters = [
        expected_attribute_data_structure[0]['attribute'],
        expected_attribute_data_structure[0]['properties']]
expected_mandatory_cmd_parameters = [
    {
        "name": 'State',
        "arginDescription": 'none',
        "arginType": PyTango._PyTango.CmdArgType.DevVoid,
        "argoutDescription": 'Device state',
        "argoutType": PyTango.utils.DevState,
        "description": 'This command gets the device state (stored in its device_state data member) and returns it to the caller.',
        "displayLevel": 'OPERATOR',
        "polledPeriod": '0',
        "execMethod": 'dev_state',
        "isDynamic": ''
    },
    {
        "arginDescription": 'none',
        "arginType": PyTango._PyTango.CmdArgType.DevVoid,
        "argoutDescription": 'Device status',
        "argoutType": PyTango._PyTango.CmdArgType.DevString,
        "description": 'This command gets the device status (stored in its device_status data member) and returns it to the caller.',
        "displayLevel": 'OPERATOR',
        "execMethod": 'dev_status',
        "name": 'Status',
        "polledPeriod": '0',
        "isDynamic": ''
     }
]


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

                if not attr_prop_value:
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
        with mock.patch(sim_xmi_parser.__name__+'.get_xmi_description_file_name'                                                 ) as mock_get_xmi_description_file_name:
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

    def test_default_parsed_device_spec(self):
        """Testing that a default POGO generated xmi has no attributes or
        properties but just two default commands.
        """
        attr_list = ['insolation', 'temperature', 'pressure', 'rainfall',
                'relativeHumidity', 'wind_direction', 'input_comms_ok',
                'wind_speed']
        self.assertEqual(set(self.xmi_parser.get_reformatted_device_attr_metadata()),
                set(attr_list),
                "The are some unexpected attributes in the list")

        default_device_commands = ['State', 'Status']
        parsed_commands = []
        for parsed_command in self.xmi_parser.device_commands:
            parsed_commands.append(parsed_command['name'])

        #self.assertEquals(2, len(parsed_commands),
         #       'The default attributes are less than or more than two')
        self.assertNotEqual(set(parsed_commands), set(default_device_commands),
                "The are some unexpected commands in the list")
        #self.assertEqual(self.xmi_parser.device_properties, [],
         #       "There are unexpected properties in the list")

        parsed_commands = self.xmi_parser.device_commands
        parsed_commands_properties = expected_mandatory_cmd_parameters[0].keys()

        for cmd_props in parsed_commands:
            if cmd_props['name'] not in ['State', 'Status']:
                self.assertEquals(set(parsed_commands_properties), set(cmd_props.keys()),
                    "One of the commands dont have the mandatory properties")

    def test_parsed_attributes(self):
        pass

    def test_parsed_commands(self):
        parsed_commands = self.xmi_parser.device_commands
        parsed_commands_properties = expected_mandatory_cmd_parameters[0].keys()

        for cmd_props in parsed_commands:
            if cmd_props['name'] not in ['State', 'Status']:
                self.assertEquals(set(parsed_commands_properties), set(cmd_props.keys()),
                    "The command %s doesn't have all the mandatory properties" % (cmd_props['name']))

        cmd_on_info = None
        for cmd_props in parsed_commands:
            if cmd_props['name'] in ['On']:
                cmd_on_info = cmd_props
                break
        self.assertEqual(cmd_on_info['description'], 'Turn On Device')
        self.assertEqual(cmd_on_info['execMethod'], 'on')
        self.assertEqual(cmd_on_info['displayLevel'], 'OPERATOR')
        self.assertEqual(cmd_on_info['polledPeriod'], '0')
        self.assertEqual(cmd_on_info['isDynamic'], 'false')
        self.assertEqual(cmd_on_info['arginDescription'], '')
        self.assertEqual(cmd_on_info['arginType'], PyTango.CmdArgType.DevVoid)
        self.assertEqual(cmd_on_info['argoutDescription'], 'ok | Device ON')
        self.assertEqual(cmd_on_info['argoutType'], PyTango.CmdArgType.DevString)

    def test_parsed_device_properties(self):
        pass
