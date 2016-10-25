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

LOGGER = logging.getLogger(__name__)

default_attributes = {'State', 'Status'}


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
        # Shot sleeping time to allow the tango device to configure
        #time.sleep(0.5)
        
    def test_attribute_list(self):
        attributes = set(self.device.get_attribute_list())
        expected_attributes = []
        for attribute_data in self.xmi_parser.device_attributes:
            expected_attributes.append(attribute_data['dynamicAttributes']['name'])
        self.assertEqual(set(expected_attributes),  attributes - default_attributes,
                         "Actual tango device attribute list differs from expected list!")

    def test_attribute_properties(self):
        attribute_list = self.device.get_attribute_list()
        
        for attribute_data in self.xmi_parser.device_attributes:
            # The properties that are tested for each the tango attributes are all
            # in the POGO_USER_DEFAULT_ATTR_PROP_MAP dict items
            for default_attr_props in (sim_xmi_parser.
                        POGO_USER_DEFAULT_ATTR_PROP_MAP.items()):
                # prop_group is the keys in the POGO_USER_DEFAULT_ATTR_PROP_MAP
                # that also match that in `self.xmi_parser.device_attributes`
                prop_group, default_attr_prop = default_attr_props
                attr_name = attribute_data['dynamicAttributes']['name']
                #print 'attr_name= ' + attr_name
                #print self.device.get_attribute_config('temperature')
                #print hasattr(self.device, attr_name)
                #self.assertEqual(hasattr(self.device, attr_name), True,
                 #                "Device does not have an attribute %s" % (attr_name))
                self.assertIn(attr_name, attribute_list,
                        "Device does not have the attribute %s" % (attr_name))
                attr_query_data = self.device.attribute_query(attr_name)
                for pogo_prop, user_default_prop in default_attr_prop.items():
                    expected_atrr_value = attribute_data[prop_group][pogo_prop]
                    attr_prop_value = getattr(attr_query_data, user_default_prop, None)
                    # Here the writable property is checked for, since Pogo
                    # expresses in as a string (e.g. 'READ') where tango device return a
                    # Pytango object `PyTango.AttrWriteType.READ` and taking
                    # its string returns 'READ' which corresponds to the Pogo one.
                    if user_default_prop in ['writable']:
                        attr_prop_value = str(attr_prop_value)
                    if not attr_prop_value:
                        # In the case where no attr_query data is not found it is
                        # further checked in the mentioned attribute object
                        # i.e. alarms and events
                        # (check `self._test_tango_property_object`)
                        attr_prop_value = self._get_attribute_property_object_value(
                                                 attr_query_data, user_default_prop)
                    # Here the data_type property is checked for, since Pogo
                    # expresses in as a PyTango object (e.g.`PyTango.DevDouble`)
                    # where tango device return a corresponding int value (e.g. 5)
                    # and taking int of `PyTango.DevDouble` returns 5.
                    if user_default_prop in ['data_type']:
                        expected_atrr_value = int(expected_atrr_value)
                    # For some reason tango device attribute properties not
                    # stated are assigned a string 'Not Specified' or even 'No
                    # writable Specified'
                    if 'No' in str(attr_prop_value):
                        attr_prop_value = ''
                    # Pogo doesn't seem to populate the format as expected i.e.
                    # format = '', and tango  device return (e.g. %6.2f for
                    # floating points)
                    if user_default_prop in ['format']:
                        attr_prop_value = ''
                    self.assertEqual(expected_atrr_value, attr_prop_value,
                            "Non matching %s property for %s attribute" % (
                                    user_default_prop, attr_name))

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
