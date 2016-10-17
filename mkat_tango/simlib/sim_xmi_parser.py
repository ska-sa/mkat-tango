import os
import sys
import time
import weakref
import logging
import argparse

import xml.etree.ElementTree as ET
import PyTango

from functools import partial
from PyTango import Attr, AttrWriteType, UserDefaultAttrProp, AttrQuality, Database
from PyTango import DevState, DevBoolean, DevString, DevEnum
from PyTango.server import Device, DeviceMeta, server_run, device_property

from mkat_tango import helper_module
from mkat_tango.simlib import quantities
from mkat_tango.simlib import model

MODULE_LOGGER = logging.getLogger(__name__)

CONSTANT_DATA_TYPES = [DevBoolean, DevEnum, DevString]

POGO_USER_DEFAULT_ATTR_PROP_MAP = {
        'format': 'format',
        'label': 'label',
        'maxAlarm': 'max_alarm',
        'maxValue': 'max_value',
        'maxWarning': 'max_warning',
        'minAlarm': 'min_alarm',
        'deltaTime': 'delta_t',
        'minValue': 'min_value',
        'deltaValue': 'delta_val',
        'minWarning': 'min_warning',
        'description': 'description',
        'polledPeriod': 'period',
        'displayUnit': 'display_unit',
        'standardUnit': 'standard_unit',
        'unit': 'unit',
        'name': 'name',
        'dataType': 'dataType',
        'rwType': 'rwType'
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
        """Data structure format is a list containing device property info in a dict

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
        # pogo_type has format -> pogoDsl:DoubleType
        # Pytango type must be of the form DevDouble
        arg_type = pogo_type.split(':')[1].replace('Type', '')
        # pogo_type for status turns out to be 'pogoDsl:ConnstStringType
        # For now it will be treated as normal DevString type
        if arg_type.find('Const') != -1:
            arg_type = arg_type.replace('Const', '')
        arg_type = getattr(PyTango, 'Dev' + arg_type)
        return arg_type

class PopulateModelQuantities(model.Model):

    def __init__(self, xmi_file, device_name):
        self.xmi_parser = Xmi_Parser(xmi_file)
        super(PopulateModelQuantities, self).__init__(device_name)
        self.setup_sim_quantities()

    def setup_sim_quantities(self):
        """Set up self.sim_quantities from Model with simulated quantities.

        Places simulated quantities in sim_quantities dict. Keyed by name of
        quantity, value must be instances satifying the
        :class:`quantities.Quantity` interface

        Notes
        =====
        - Must use self.start_time to set initial time values.
        - Must call super method after setting up `sim_quantities`

        """
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)
        for attribute_info in self.xmi_parser.device_attributes:
            attribute_meta = {}
            for prop, prop_default in POGO_USER_DEFAULT_ATTR_PROP_MAP.items():
                attribute_meta[prop_default] = attribute_info[prop]
            if attribute_info['dataType'] in CONSTANT_DATA_TYPES:
                self.sim_quantities[attribute_meta['name']] = ConstantQuantity(
                        meta=attribute_meta, start_value=True)
            else:
                try:
                    sim_attr_quantities = self.sim_attribute_quantities(
                        float(attribute_meta['min_value']),
                        float(attribute_meta['max_value']))
                except ValueError:
                    raise NotImplementedError('Attribute min or max not specified')
                self.sim_quantities[attribute_meta['name']] = GaussianSlewLimited(
                        meta=attribute_meta, **sim_attr_quantities)

    def sim_attribute_quantities(self, min_value, max_value, slew_rate=None):
        """Simulate attribute quantities with a Guassian value distribution

        Parameters
        ==========
        min_value : float
            minimum attribute value to be simulated
        max_value : float
            maximum attribute value to be simulated
        slew_rate : float
            maximum changing rate of the simulated quantities between min and max values

        Returns
        ======
        sim_attribute_quantities : dict
            Dict of Gaussian simulated quantities

        Notes
        =====
        - Statistical simulation parameters (mean, std dev, slew rate) are derived from the 
          min/max values of the attribute.

        """
        sim_attribute_quantities = dict()
        if slew_rate:
            max_slew_rate = slew_rate
        else:
            # A hard coded value is computed as follows
            max_slew_rate = (max_value + abs(min_value))/10.0
        sim_attribute_quantities['max_slew_rate'] = max_slew_rate
        sim_attribute_quantities['min_bound'] = min_value
        sim_attribute_quantities['max_bound'] = max_value
        # TODO (AR) 2016-10-14: In the future we might define a way to specify
        # simulation defaults or simulation bounds different from the XMI bounds
        sim_attribute_quantities['mean'] = (max_value - min_value)/2
        sim_attribute_quantities['std_dev'] = max_slew_rate/2
        return sim_attribute_quantities


class TangoDeviceServer(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()

    sim_xmi_description_file = device_property(dtype=str,
            doc='Complete path name of the POGO xmi file to be parsed')

    def init_device(self):
        super(TangoDeviceServer, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        xmi_file = get_xmi_description_file_name()
        self.model = PopulateModelQuantities(xmi_file, name)
        self.set_state(DevState.ON)

    def initialize_dynamic_attributes(self):
        """The device method that sets up attributes during run time"""
        model_sim_quants = self.model.sim_quantities
        attribute_list = set([attr for attr in model_sim_quants.keys()])

        for attribute_name in attribute_list:
            MODULE_LOGGER.info("Added dynamic {} attribute"
                               .format(attribute_name))
            meta_data = model_sim_quants[attribute_name].meta
            attr_dtype = meta_data['dataType']
            # The return value of rwType is a string and it is required as a
            # PyTango data type when passed to the Attr function.
            # e.g. 'READ' -> PyTango.AttrWriteType.READ
            rw_type = meta_data['rwType']
            rw_type = getattr(AttrWriteType, rw_type)
            attr = Attr(attribute_name, attr_dtype, rw_type)
            attr_props = UserDefaultAttrProp()
            for prop in meta_data.keys():
                attr_prop_setter = getattr(attr_props, 'set_' + prop, None)
                if attr_prop_setter:
                    attr_prop_setter(meta_data[prop])
                else:
                    MODULE_LOGGER.info("No setter function for " + prop + " property")
            attr.set_default_properties(attr_props)
            self.add_attribute(attr, self.read_attributes)

    def always_executed_hook(self):
        self.model.update()

    def read_attributes(self, attr):
        """Method reading an attribute value

        Parameters
        ==========

        attr : PyTango.DevAttr
            The attribute to read from.

        """
        name = attr.get_name()
        value, update_time = self.model.quantity_state[name]
        quality = AttrQuality.ATTR_VALID
        self.info_stream("Reading attribute %s", name)
        attr.set_value_date_quality(value, update_time, quality)

def get_xmi_description_file_name():
    """Gets the xmi description file name from the tango-db device properties

    Returns
    =======
    sim_xmi_description_file : str
        POGO xmi device server description file
        e.g. 'home/user/weather.xmi'

    """
    server_name = helper_module.get_server_name()
    db = Database()
    server_class = db.get_server_class_list(server_name).value_string[0]
    device_name = db.get_device_name(server_name, server_class).value_string[0]
    sim_xmi_description_file = db.get_device_property(device_name,
        'sim_xmi_description_file')['sim_xmi_description_file'][0]
    return sim_xmi_description_file

def main():
    server_run([TangoDeviceServer])

if __name__ == "__main__":
    main()
