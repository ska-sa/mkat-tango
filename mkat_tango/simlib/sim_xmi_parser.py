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
        print self.device_properties
        print self.device_attributes
        print self.device_commands

    def sim_description_data(self):
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
        command = {}
        command['name'] = description_data.attrib['name']
        command['description'] = description_data.attrib['description']
        input_parameter = description_data.find('argin')
        command['arginDescription'] = input_parameter.attrib['description']
        command['arginType'] = self._get_arg_type(input_parameter)
        output_parameter = description_data.find('argout')
        command['argoutDescription'] = output_parameter.attrib['description']
        command['argoutType'] = self._get_arg_type(output_parameter)
        return command

    def attributes_description_data(self, description_data):
        attribute = {}
        attribute_properties = description_data.find('properties')
        attribute['name'] = description_data.attrib['name']
        attribute['dataShape'] = description_data.attrib['attType']
        attribute['readWriteProperty'] = description_data.attrib['rwType']
        attribute['displayLevel'] = description_data.attrib['displayLevel']
        attribute['polledPeriod'] = description_data.attrib['polledPeriod']
        attribute['description'] = attribute_properties.attrib['description']
        attribute['label'] = attribute_properties.attrib['label']
        attribute['unit'] = attribute_properties.attrib['unit']
        attribute['dataType'] = self._get_arg_type(description_data)
        attribute['minValue'] = attribute_properties.attrib['minValue']
        attribute['maxValue'] = attribute_properties.attrib['maxValue']
        attribute['minAlarm'] = attribute_properties.attrib['minAlarm']
        attribute['maxAlarm'] = attribute_properties.attrib['maxAlarm']
        attribute['minWarning'] = attribute_properties.attrib['minWarning']
        attribute['maxWarning'] = attribute_properties.attrib['maxWarning']
        return attribute

    def device_property_description_data(self, description_data):
        device_property = {}
        device_property['name'] = description_data.attrib['name']
        device_property['description'] = description_data.attrib['description']
        device_property['type'] = self._get_arg_type(description_data)
        device_property['defaultPropValue'] = description_data.find(
                                                'DefaultPropValue').text
        return device_property

    def _get_arg_type(self, parameter):
        if parameter.tag in ['attributes', 'dynamicAttributes']:
            pogo_type = parameter.find('dataType').attrib.values()[0]
        else:
            pogo_type = parameter.find('type').attrib.values()[0]
        arg_type = POGO2TANGO_TYPE[pogo_type]
        return arg_type
