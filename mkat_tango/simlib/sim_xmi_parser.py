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
from PyTango import DevState, DevBoolean, DevString, DevEnum, AttrDataFormat, CmdArgType
from PyTango.server import Device, DeviceMeta, server_run, device_property, command

from mkat_tango import helper_module
from mkat_tango.simlib import quantities
from mkat_tango.simlib import model

MODULE_LOGGER = logging.getLogger(__name__)

CONSTANT_DATA_TYPES = [DevBoolean, DevEnum, DevString]
POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP = {
        'Image': AttrDataFormat.IMAGE,
        'Scalar': AttrDataFormat.SCALAR,
        'Spectrum': AttrDataFormat.SPECTRUM}

# TODO(KM 31-10-2016): Need to xmi attributes properties that are currently
# not being handled by the parser e.g. [displayLevel, enumLabels] etc.
POGO_USER_DEFAULT_ATTR_PROP_MAP = {
        'dynamicAttributes': {
            'name': 'name',
            'dataType': 'data_type',
            'rwType': 'writable',
            'polledPeriod': 'period',
            'attType': 'data_format',
            'maxX': 'max_dim_x',
            'maxY': 'max_dim_y'},
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

POGO_USER_DEFAULT_CMD_PROP_MAP = {
        'name': 'name',
        'arginDescription': 'doc_in',
        'arginType': 'dtype_in',
        'argoutDescription': 'doc_out',
        'argoutType': 'dtype_out'}

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
        # TODO(KM 31-10-2016): Need to also parse the class properties.
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

        attType =  attribute_data['dynamicAttributes']['attType']
        if attType in POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP.keys():
            attribute_data['dynamicAttributes']['attType'] = (
                    POGO_PYTANGO_ATTR_FORMAT_TYPES_MAP[attType])

        attribute_data['dynamicAttributes']['maxX'] = (1
                if attribute_data['dynamicAttributes']['maxX'] == ''
                else int(attribute_data['dynamicAttributes']['maxX']))
        attribute_data['dynamicAttributes']['maxY'] = (0
                if attribute_data['dynamicAttributes']['maxY'] == ''
                else int(attribute_data['dynamicAttributes']['maxY']))


        attribute_data['dynamicAttributes']['dataType'] = self._get_arg_type(description_data)
        attribute_data['properties'] = description_data.find('properties').attrib
        # TODO(KM 31-10-2016): Events information is not mandatory for attributes, need
        # to handle this properly as it raises an AttributeError error when trying to
        # parse an xmi file with an attribute with not event information specified.
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
        # The out_type of the device State command is PyTango._PyTango.CmdArgType.DevState
        # instead of the default PyTango.utils.DevState
        if arg_type == 'State':
            return CmdArgType.DevState
        arg_type = getattr(PyTango, 'Dev' + arg_type)
        return arg_type


    def get_reformatted_device_attr_metadata(self):
        """Converts the device_attributes data structure into a dictionary
        to make searching easier.

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

    def get_reformatted_cmd_metadata(self):
        """Converts the device_commands data structure into a dictionary that
        makes searching easier.

        Returns
        -------
        commands : dict
            A dictionary of all the device commands together with their
            metadata specified in the POGO generated XMI file. The key
            represents the name of the command and the value is a dictionary
            of all the attribute's metadata.

            e.g. { 'cmd_name': {cmd_properties}

                 }
        """
        commands = {}
        for cmd_info in self.device_commands:
            commands[cmd_info['name']] = cmd_info

        new_commands = {}
        # Need to convert the parameter names to the TANGO names
        for cmd_name, cmd_metadata in commands.items():
            new_commands_metadata = {}
            for cmd_prop_name, cmd_prop_value in cmd_metadata.items():
                try:
                    new_commands_metadata.update(
                            {POGO_USER_DEFAULT_CMD_PROP_MAP[cmd_prop_name] :cmd_prop_value})
                except KeyError:
                    MODULE_LOGGER.info("The property '%s' cannot be translated to a "
                            "corresponding parameter in the TANGO library" %(cmd_prop_name))

            new_commands[cmd_name] = new_commands_metadata

        return new_commands

    def get_reformatted_properties_metadata(self):
        """Creates a dictionary of the device properties and their metadata.

        Returns
        -------
        device_properties: dict
            A dictionary of all the device properties together with their
            metadata specified in the POGO generated XMI file. The keys
            represent the name of the device property and the value is a
            dictionary of all the property's metadata.

            e.g. { 'device_property_name' : {device_property_metadata}

                 }

        """
        device_properties = {}
        for properties_info in self.device_properties:
            device_properties[properties_info['deviceProperties']['name']] = (
                    properties_info['deviceProperties'])

        return device_properties

class PopulateModelQuantities(object):
    """Used to populate/update model quantities.

    Populates the model quantities using the data from the TANGO device information
    captured in the POGO generated xmi file.

    Attributes
    ----------
    xmi_parser: Xmi_Parser innstance
        The Xmi_Parser object which reads an xmi file and parses it into device
        attributes, commands, and properties.
    sim_model:  Model instance
        An instance of the Model class which is used for simulation of simple attributes.
    """
    def __init__(self, xmi_file, tango_device_name, sim_model=None):
        self.xmi_parser = Xmi_Parser(xmi_file)
        if sim_model:
            if isinstance(sim_model, model.Model):
                self.sim_model = sim_model
            else:
                raise SimModelException("The sim_model object passed is not an "
                    "instance of the class mkat_tango.simlib.model.Model")

        else:
            self.sim_model = model.Model(tango_device_name)
        self.setup_sim_quantities()
        pma = PopulateModelActions(
                  self.xmi_parser.get_reformatted_cmd_metadata(),
                  tango_device_name,
                  model_instance=self.sim_model)

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
    derived      derived from the min/max values of the attribute.

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


class PopulateModelActions(object):
    """

    Attributes
    ----------
        command_info :

        sim_model :
    """
    def __init__(self, commands_info, tango_device_name, model_instance=None):
        self.command_info = commands_info
        if model_instance is None:
            self.sim_model = model.Model(tango_device_name)
        else:
            self.sim_model = model_instance

        self.add_actions()

    def add_actions(self):
        for cmd_name, cmd_meta in self.command_info.items():
            # Generate handler
            if cmd_name not in ['State', 'Status']:
                handler = self.generate_action_handler(cmd_name)
                self.sim_model.setup_sim_actions(cmd_name, handler)
                # Might store the action's metadata in the sim_actions dictionary
                # instead of creating a separate dict.
                self.sim_model.sim_actions_meta[cmd_name] = cmd_meta

    def generate_action_handler(self, action_name):
        def action_handler(*args):
            return 'action executed'
        action_handler.__name__ = action_name
        return action_handler


class SimModelException(Exception):
    def __init__(self, message):
        super(SimModelException, self).__init__(message)

class TangoDeviceServerBase(Device):
    instances = weakref.WeakValueDictionary()

    sim_xmi_description_file = device_property(dtype=str,
            doc='Complete path name of the POGO xmi file to be parsed')

    def init_device(self):
        super(TangoDeviceServerBase, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        self.model = None
        self.set_state(DevState.ON)

    def initialize_dynamic_attributes(self):
        """The device method that sets up attributes during run time"""
        pass

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

    # TODO (NM 2016-11-04) At the moment this is hardcoded to assume only the
    # first class and first device configures the XMI file. But more
    # fundamentally, this is a chicken and egg problem. TANGO usually assumes
    # that a device server knows what TANGO classes it supports even before any
    # device have been registered to the device server, allowing e.g. the Jive
    # server wizard to work. Now we are forcing the user to register a device
    # first to specify the XMI file. Passing the XMI file on the command line is
    # problematic since we still want to use the TANGO main function.
    #
    # Potential solutions
    #
    # 1) Generate a script that hardcodes the name of the XMI file for each
    #    dynamic device (perhaps a good simple solution, also gives you unique
    #    device server names)
    #
    # 2) Use an OS environment variable (probably too magic)
    #
    # 3) Perhaps define a "DynamicControl" class that is always exposed by the
    #    dynamic simulator. A property can then be defined on a DynamicControl
    #    instance, that is used to find the XMI file. Once the device is
    #    restarted, the classes defined in the XMI file can be exposed.

    This function should perhaps take the device name

    server_name = helper_module.get_server_name()
    db = Database()
    server_class = db.get_server_class_list(server_name).value_string[0]
    device_name = db.get_device_name(server_name, server_class).value_string[0]
    sim_xmi_description_file = db.get_device_property(device_name,
        'sim_xmi_description_file')['sim_xmi_description_file'][0]
    return sim_xmi_description_file


def get_tango_device_server(model):
    """Declares a tango device class that inherits the Device class and then
    adds tango commands.

    Returns
    -------
    TangoDeviceServer : PyTango.Device
        Tango device that has the results of the translated KATCP server

    """
    # Declare a Tango Device class for specifically adding commands prior
    # running the device server
    class TangoDeviceServerCommands(object):
        pass


    def generate_cmd_handler(action, action_handler):
        # You might need to figure out how to specialise cmd_handler to different
        # argument types
        def cmd_handler( args):
            return action_handler(args)
        cmd_handler.__name__ = action
        cmd_info_copy = model.sim_actions_meta[action].copy()
        cmd_info_copy.pop('name')
        return command(**cmd_info_copy)(cmd_handler)

    for action_name, action_handler in model.sim_actions.items():
        cmd_handler = generate_cmd_handler(action_name, action_handler)
        # You might need to turn cmd_handler into an unbound method before you add
        # it to the class
        setattr(TangoDeviceServerCommands, action_name, cmd_handler)

    class TangoDeviceServer(TangoDeviceServerBase, TangoDeviceServerCommands):
        __metaclass__ = DeviceMeta

        def initialize_dynamic_attributes(self):
            print "Overriding superclass method"
            self.model = model
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


    return TangoDeviceServer

def configure_device_model(sim_xmi_file=None, test_device_name=None):
    """In essence this function should get the xmi file, parse it,
    take the attribute and command information, populate the model quantities and
    actions to be simulated and return that model.
    """
    if sim_xmi_file is None:
        xmi_file = get_xmi_description_file_name()
    else:
        xmi_file = sim_xmi_file

    server_name = helper_module.get_server_name()

    if test_device_name is None:
        db = Database()
        db_datum = db.get_device_class_list(server_name)
        dev_name = getattr(db_datum, 'value_string')[2]
    else:
        dev_name = test_device_name

    model_quants_populater = PopulateModelQuantities(xmi_file, dev_name)
    model = model_quants_populater.sim_model
    xmi_parser = model_quants_populater.xmi_parser
    cmd_info = xmi_parser.get_reformatted_cmd_metadata()
    PopulateModelActions(cmd_info, dev_name, model)

    return model

def main():
    model = configure_device_model()
    TangoDeviceServer = get_tango_device_server(model)
    server_run([TangoDeviceServer])

if __name__ == "__main__":
    main()
