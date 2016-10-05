import time
import logging

import xml.etree.ElementTree as ET

from PyTango import (DevDouble, DevShort, DevUShort, DevState,
                     DevLong, DevULong, DevLong64, DevULong64,
                     DevBoolean, DevString, DevVoid, DevEnum,
                     DevVarDoubleArray, DevVarStringArray)

MODULE_LOGGER = logging.getLogger(__name__)

POGO2TANGO_TYPE = {
        'pogoDsl:VoidType': DevVoid,
        'pogoDsl:StringType': DevString,
        'pogoDsl:DoubleType': DevDouble,
        'pogoDsl:ConstStringType': DevString,
        'pogoDsl:DoubleArrayType': DevVarDoubleArray,
        'pogoDsl:StringArrayType': DevVarStringArray,
        'pogoDsl:StateType': DevState,
        'pogoDsl:BooleanType': DevBoolean
        }


class Xmi_Parser(object):

    def __init__(self, xmi_file):
        self.xmi_file = xmi_file
        self.device_class_name = ''
        self.device_attributes = []
        """The Data structure format is a list containing attribute info in a dict

        e.g.[{'name': 'wind_speed', 'dataShape': 'Scalar',
            'dataType': tango._tango.CmdArgType.DevDouble,
            'description': 'Wind speed in central telescope area.',
            'displayLevel': 'EXPERT', 'label': 'Wind speed', 'maxAlarm': '25',
            'maxValue': '30', 'maxWarning': '15', 'minAlarm': '', 'minValue': '0',
            'minWarning': '','name': 'wind_speed', 'polledPeriod': '3000',
            'readWriteProperty': 'READ', 'unit': 'm/s'}, ...]

        """
        self.device_commands = []
        """The Data structure format is a list containing command info in a dict
        e.g.[{'name': 'On', 'arginDescription': '',
            'arginType': tango._tango.CmdArgType.DevVoid,
            'argoutDescription': 'ok | Device ON',
            'argoutType': tango._tango.CmdArgType.DevString,
            'description': 'Turn On Device'}, ...]

        """
        self.device_properties = []
        """The Data structure format is a list containing device property info in a
            dict

        e.g.[{'name': 'katcp_address', 'defaultPropValue': '127.0.0.1',
                  'description': '', 'type': tango._tango.CmdArgType.DevString},

        """
        self.sim_description_data()

    def sim_description_data(self):
        """
        Read simulator description data from xmi file into `self.device_properties`
        
        
        Stores all the simulator description data from the xmi tree into
        appropriate attribute, command and device property data structures.
        Loops through the xmi tree class elements and appends description
        information of dynamic/attributes into `self.device_attributes`,
        commands into `self.device_commands`, and device_properties into
        `self.device_properties`.

        Notes
        =====
        - Data structures, are type list with dictionary elements keyed with
          description data and values must be the corresponding data value.

        """
        tree = ET.parse(self.xmi_file)
        root = tree.getroot()
        device_class = root.find('classes')
        self.device_class_name = device_class.attrib['name']
        for class_description_data in device_class:
            if class_description_data.tag in ['commands']:
                command_info = self.command_description_data(class_description_data)
                self.device_commands.append(command_info)
            elif class_description_data.tag in ['dynamicAttributes', 'attributes']:
                attribute_info = self.attributes_description_data(
                                            class_description_data)
                self.device_attributes.append(attribute_info)
            elif class_description_data.tag in ['deviceProperties']:
                device_property_info = self.device_property_description_data(
                                                       class_description_data)
                self.device_properties.append(device_property_info)

    def command_description_data(self, description_data):
        """Extract command description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with command data, where
            expected element tag(s) are (i.e. description_data.tag)
            ['argin', 'argout'] and
            description_data.attrib contains
            {'description': 'Turn On Device',
            'displayLevel': 'OPERATOR',
            'execMethod': 'on',
            'isDynamic': 'false',
            'name': 'On',
            'polledPeriod': '0'}

        Returns
        -------
        command_data: dict
            Dictionary of all the command data required to create a tango command

        """
        command_data = description_data.attrib
        input_parameter = description_data.find('argin')
        command_data['arginDescription'] = input_parameter.attrib['description']
        command_data['arginType'] = self._get_arg_type(input_parameter)
        output_parameter = description_data.find('argout')
        command_data['argoutDescription'] = output_parameter.attrib['description']
        command_data['argoutType'] = self._get_arg_type(output_parameter)
        return command_data

    def attributes_description_data(self, description_data):
        """Extract attribute description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with attribute data

            Expected element tag(s) are (i.e. description_data.tag)
            ['properties']

            description_data.find('properties').attrib contains
            {'deltaTime': '', 'deltaValue': '', 'description': '',
             'displayUnit': '', 'format': '', 'label': '',
             'maxAlarm': '', 'maxValue': '', 'maxWarning': '',
             'minAlarm': '', 'minValue': '', 'minWarning': '',
             'standardUnit': '', 'unit': ''} and

            description_data.attrib contains
            {'allocReadMember': 'false',
            'attType': 'Scalar',
            'displayLevel': 'OPERATOR',
            'isDynamic': 'false',
            'maxX': '',
            'maxY': '',
            'name': 'Constant',
            'polledPeriod': '0',
            'rwType': 'WRITE'}

        Returns
        -------
        attribute_data: dict
            Dictionary of all attribute data required to create a tango attribute

        """
        attribute_data = description_data.attrib
        attribute_properties = description_data.find('properties')
        attribute_data.update(attribute_properties.attrib)
        attribute_data['dataType'] = self._get_arg_type(description_data)
        return attribute_data

    def device_property_description_data(self, description_data):
        """Extract device property description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device property data

            Expected element tag(s) are (i.e. description_data.tag)
            ['DefaultPropValue']

            description_data.attrib contains
            {'description': '', 'name': 'katcp_address'}

        Returns
        -------
        device_property_data: dict
            Dictionary of all device property data required
            to create a tango device property

        """
        device_property_data = description_data.attrib
        device_property_data['type'] = self._get_arg_type(description_data)
        device_property_data['defaultPropValue'] = description_data.find(
                                                'DefaultPropValue').text
        return device_property_data

    def _get_arg_type(self, description_data):
        """Extract argument data type from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device_property or attribute or command data

            Expected element tag(s) are (i.e. description_data.tag)
            ['dataType'] for attributes and dynamicAttributes
            ['type'] for commands and deviceProperties

        Returns
        -------
        arg_type: tango._tango.CmdArgType
            Tango argument type

        """
        if description_data.tag in ['attributes', 'dynamicAttributes']:
            pogo_type = description_data.find('dataType').attrib.values()[0]
        else:
            pogo_type = description_data.find('type').attrib.values()[0]
        arg_type = POGO2TANGO_TYPE[pogo_type]
        return arg_type
