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
        'dynamicAttributes': {
            'name': 'name',
            'dataType': 'data_type',
            'rwType': 'writable',
            'polledPeriod': 'period'},
        'eventArchiveCriteria': {
            'absChange': 'archive_abs_change',
            'period': 'archive_period',
            'relChange': 'archive_rel_change'},
        'eventCriteria': {
            'absChange': 'abs_change',
            'period': 'event_period',
            'relChange': 'rel_change'},
        'properties': {
            'maxAlarm': 'max_alarm',
            'maxValue': 'max_value',
            'maxWarning': 'max_warning',
            'minAlarm': 'min_alarm',
            'deltaTime': 'delta_t',
            'minValue': 'min_value',
            'deltaValue': 'delta_val',
            'minWarning': 'min_warning',
            'description': 'description',
            'displayUnit': 'display_unit',
            'standardUnit': 'standard_unit',
            'format': 'format',
            'label': 'label',
            'unit': 'unit'}
        }


class Xmi_Parser(object):

    def __init__(self, xmi_file):
        self.xmi_file = xmi_file
        self.device_class_name = ''
        self.device_attributes = []
        """The Data structure format is a list containing attribute info in a dict

        e.g.
        [{
            "attribute": {
                "displayLevel": "OPERATOR",
                "maxX": "",
                "maxY": "",
                "attType": "Scalar",
                "polledPeriod": "1000",
                "dataType": DevDouble,
                "isDynamic": "true",
                "rwType": "READ",
                "allocReadMember": "true",
                "name": "temperature"
            },
            "eventCriteria": {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            },
            "evArchiveCriteria": {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            },
            "properties": {
                "description": "Current temperature outside near the telescope.",
                "deltaValue": "",
                "maxAlarm": "50",
                "maxValue": "51",
                "minValue": "-10",
                "standardUnit": "",
                "minAlarm": "-9",
                "maxWarning": "45",
                "unit": "Degrees Centrigrade",
                "displayUnit": "",
                "format": "",
                "deltaTime": "",
                "label": "Outside Temperature",
                "minWarning": "-5"
           }
        }]

        """
        self.device_commands = []
        """The Data structure format is a list containing command info in a dict

        e.g.
        [{
             "name": "On",
             "arginDescription": "",
             "arginType": tango._tango.CmdArgType.DevVoid,
             "argoutDescription": "ok | Device ON",
             "argoutType": tango._tango.CmdArgType.DevString,
             "description": "Turn On Device"
        }]
        """
        self.device_properties = []
        """Data structure format is a list containing device property info in a dict

        e.g.
        [{
            "deviceProperties": {
                "type": DevString,
                "mandatory": "true",
                "description": "Path to the pogo generate xmi file",
                "name": "sim_xmi_description_file"
            }
        }]
        """
        self.parse_xmi_file()

    def parse_xmi_file(self):
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
                command_info = (
                    self.extract_command_description_data(class_description_data))
                self.device_commands.append(command_info)
            elif class_description_data.tag in ['dynamicAttributes', 'attributes']:
                attribute_info = self.extract_attributes_description_data(
                                            class_description_data)
                self.device_attributes.append(attribute_info)
            elif class_description_data.tag in ['deviceProperties']:
                device_property_info = self.extract_device_property_description_data(
                                                       class_description_data)
                self.device_properties.append(device_property_info)

    def extract_command_description_data(self, description_data):
        """Extract command description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with command data, where
            expected element tag(s) are (i.e. description_data.tag)
            ['argin', 'argout'] and
            description_data.attrib contains
            {
                "description": "Turn On Device",
                "displayLevel": "OPERATOR",
                "isDynamic": "false",
                "execMethod": "on",
                "polledPeriod": "0",
                "name": "On"
            }

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

    def extract_attributes_description_data(self, description_data):
        """Extract attribute description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with attribute data

            Expected element tag(s) are (i.e. description_data.tag)
            'dynamicAttributes'

            description_data.find('properties').attrib contains
            {
                "description": "",
                "deltaValue": "",
                "maxAlarm": "",
                "maxValue": "",
                "minValue": "",
                "standardUnit": "",
                "minAlarm": "",
                "maxWarning": "",
                "unit": "",
                "displayUnit": "",
                "format": "",
                "deltaTime": "",
                "label": "",
                "minWarning": ""
            }

            and

            description_data.attrib contains
            {
                "maxX": "",
                "maxY": "",
                "attType": "Scalar",
                "polledPeriod": "0",
                "displayLevel": "OPERATOR",
                "isDynamic": "false",
                "rwType": "WRITE",
                "allocReadMember": "false",
                "name": "Constant"
            }



            description_data.find('eventCriteria').attrib contains
            {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            }

            description_data.find('evArchiveCriteria').attrib contains
            {
                "relChange": "10",
                "absChange": "0.5",
                "period": "1000"
            }

        Returns
        -------
        attribute_data: dict
            Dictionary of all attribute data required to create a tango attribute

        """
        attribute_data = dict()
        attribute_data['dynamicAttributes'] = description_data.attrib
        attribute_data['dynamicAttributes']['dataType'] = self._get_arg_type(description_data)
        attribute_data['properties'] = description_data.find('properties').attrib
        attribute_data['eventCriteria'] = description_data.find('eventCriteria').attrib
        attribute_data['eventArchiveCriteria'] = description_data.find(
            'evArchiveCriteria').attrib
        return attribute_data

    def extract_device_property_description_data(self, description_data):
        """Extract device property description data from the xmi tree element.

        Parameters
        ----------
        description_data: xml.etree.ElementTree.Element
            XMI tree element with device property data

            Expected element tag(s) are (i.e. description_data.tag)
            ['DefaultPropValue']

            description_data.attrib contains
            {
                'description': '',
                'name': 'katcp_address'
            }

        Returns
        -------
        device_property_data: dict
            Dictionary of all device property data required
            to create a tango device property

        """
        device_property_data = dict()
        device_property_data['deviceProperties'] = description_data.attrib
        device_property_data['deviceProperties']['type'] = (
                self._get_arg_type(description_data))
        if description_data.find('defaultPropValue'):
            device_property_data['deviceProperties']['defaultPropValue'] = (
                 description_data.find('defaultPropValue').text)
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
        # pogo_type for status turns out to be 'pogoDsl:ConstStringType
        # For now it will be treated as normal DevString type
        if arg_type.find('Const') != -1:
            arg_type = arg_type.replace('Const', '')
        arg_type = getattr(PyTango, 'Dev' + arg_type)
        return arg_type


    def get_reformatted_device_attr_metadata(self):
        """Extracts all the necessary attribute metadata from the device_attribute data
        structure.

        Returns
        -------
        attributes: dict
            A dictionary of all the device attributes together with their
            metadata specified in the POGO generated XMI file. The key 
            represents the name of the attribute and the value is a dictionary
            of all the attribute's metadata.

            e.g.
            {'input_comms_ok': {
                'abs_change': '',
                'archive_abs_change': '',
                'archive_period': '1000',
                'archive_rel_change': '',
                'data_type': PyTango._PyTango.CmdArgType.DevBoolean,
                'delta_t': '',
                'delta_val': '',
                'description': 'Communications with all weather sensors are nominal.',
                'display_unit': '',
                'event_period': '1000',
                'format': '',
                'label': 'Input communication OK',
                'max_alarm': '',
                'max_value': '',
                'max_warning': '',
                'min_alarm': '',
                'min_value': '',
                'min_warning': '',
                'name': 'input_comms_ok',
                'period': '1000',
                'rel_change': '',
                'standard_unit': '',
                'unit': '',
                'writable': 'READ'},
            }

        """
        attributes = {}

        for pogo_attribute_data in self.device_attributes:
            attribute_meta = {}
            for (prop_group, default_attr_props) in (
                    POGO_USER_DEFAULT_ATTR_PROP_MAP.items()):
                for pogo_prop, user_default_prop in default_attr_props.items():
                    attribute_meta[user_default_prop] = (
                            pogo_attribute_data[prop_group][pogo_prop])
            attributes[attribute_meta['name']] = attribute_meta
        return attributes

class PopulateModelQuantities(object):
    """
    """
    def __init__(self, xmi_file, tango_device_name, sim_model=None):
        self.xmi_parser = Xmi_Parser(xmi_file)
        if sim_model:
            self.sim_model = sim_model
        else:
            self.sim_model = model.Model(tango_device_name)
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
        start_time = self.sim_model.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)
        attributes = self.xmi_parser.get_reformatted_device_attr_metadata()

        for attr_name, attr_props in attributes.items():
            if attr_props['data_type'] in CONSTANT_DATA_TYPES:
                        self.sim_model.sim_quantities[
                        attr_props['name']] = ConstantQuantity(
                                meta=attr_props, start_value=True)
            else:
                try:
                    sim_attr_quantities = self.sim_attribute_quantities(
                            float(attr_props['min_value']),
                            float(attr_props['max_value']))
                except ValueError:
                    raise NotImplementedError(
                            'Attribute min or max not specified')
                self.sim_model.sim_quantities[
                        attr_props['name']] = GaussianSlewLimited(
                                meta=attr_props, **sim_attr_quantities)

    def sim_attribute_quantities(self, min_value, max_value, slew_rate=None):
        """Simulate attribute quantities with a Guassian value distribution

        Parameters
        ==========
        min_value : float
            minimum attribute value to be simulated
        max_value : float
            maximum attribute value to be simulated
        slew_rate : float
            maximum changing rate of the simulated quantities between min
            and max values

        Returns
        ======
        sim_attribute_quantities : dict
            Dict of Gaussian simulated quantities

        Notes
        =====
        - Statistical simulation parameters (mean, std dev, slew rate) are
          derived from the min/max values of the attribute.

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
        self.model = PopulateModelQuantities(xmi_file, name).sim_model
        self.set_state(DevState.ON)

    def initialize_dynamic_attributes(self):
        """The device method that sets up attributes during run time"""
        model_sim_quants = self.model.sim_quantities
        attribute_list = set([attr for attr in model_sim_quants.keys()])
        for attribute_name in attribute_list:
            MODULE_LOGGER.info("Added dynamic {} attribute"
                               .format(attribute_name))
            meta_data = model_sim_quants[attribute_name].meta
            attr_dtype = meta_data['data_type']
            # The return value of rwType is a string and it is required as a
            # PyTango data type when passed to the Attr function.
            # e.g. 'READ' -> PyTango.AttrWriteType.READ
            rw_type = meta_data['writable']
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
