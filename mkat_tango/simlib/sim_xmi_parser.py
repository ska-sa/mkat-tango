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

    def __init__(self, xmi_file=None):
        self.xmi_file = xmi_file
        self.device_class_name = ''
        self.device_attributes = []
        self.device_commands = []
        self.device_properties = []
        if self.xmi_file:
            self.sim_description_data()
        else:
            raise IOError("No XMI file specified.")

    def sim_description_data(self):
        """This methods adds all the simulator description data from the xmi
        tree to appropriate data structures.

        """
        try:
            tree = ET.parse(self.xmi_file)
            root = tree.getroot()
            device_class = root.find('classes')
            self.device_class_name = device_class.attrib['name']
            self.description_data = device_class.find('description')
            for description_data in device_class:
                if description_data.tag in ['commands']:
                    command = self.command_descriptio_data(description_data)
                    self.device_commands.append(command)
                elif description_data.tag in ['dynamicAttributes', 'attributes']:
                    attribute = self.attributes_description_data(description_data)
                    self.device_attributes.append(attribute)
                elif description_data.tag in ['deviceProperties']:
                    device_property = self.device_property_description_data(
                            description_data)
                    self.device_properties.append(device_property)
        except IOError as nierr:
            MODULE_LOGGER.info(str(nierr))

    def command_descriptio_data(self, description_data):
        """Extract command description data from the xmi tree element.

        Parameters
        ---------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with command data

        Returns
        -------
        command_data: dict
            Dictionary of command data as prescribed in the SIMDD

        """
        command_data = {}
        command_data['name'] = description_data.attrib['name']
        command_data['description'] = description_data.attrib['description']
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
        ---------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with attribute data

        Returns
        -------
        attribute_data: dict
            Dictionary of attribute data as prescribed in the SIMDD

        """
        attribute_data = {}
        attribute_properties = description_data.find('properties')
        attribute_data['name'] = description_data.attrib['name']
        attribute_data['dataShape'] = description_data.attrib['attType']
        attribute_data['readWriteProperty'] = description_data.attrib['rwType']
        attribute_data['displayLevel'] = description_data.attrib['displayLevel']
        attribute_data['polledPeriod'] = description_data.attrib['polledPeriod']
        attribute_data['description'] = attribute_properties.attrib['description']
        attribute_data['label'] = attribute_properties.attrib['label']
        attribute_data['unit'] = attribute_properties.attrib['unit']
        attribute_data['dataType'] = self._get_arg_type(description_data)
        attribute_data['minValue'] = attribute_properties.attrib['minValue']
        attribute_data['maxValue'] = attribute_properties.attrib['maxValue']
        attribute_data['minAlarm'] = attribute_properties.attrib['minAlarm']
        attribute_data['maxAlarm'] = attribute_properties.attrib['maxAlarm']
        attribute_data['minWarning'] = attribute_properties.attrib['minWarning']
        attribute_data['maxWarning'] = attribute_properties.attrib['maxWarning']
        return attribute_data

    def device_property_description_data(self, description_data):
        """Extract device property description data from the xmi tree element.

        Parameters
        ---------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device property data

        Returns
        -------
        device_property_data: dict
            Dictionary of device proerty data as prescribed in the SIMDD

        """
        device_property_data = {}
        device_property_data['name'] = description_data.attrib['name']
        device_property_data['description'] = description_data.attrib['description']
        device_property_data['type'] = self._get_arg_type(description_data)
        device_property_data['defaultPropValue'] = description_data.find(
                                                'DefaultPropValue').text
        return device_property_data

    def _get_arg_type(self, description_data):
        """Extract argument data type from the xmi tree element.

        Parameters
        ---------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device_property or attribute or command data

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
