import os
import sys
import time
import logging

import json

from mkat_tango.simlib import model
from mkat_tango.simlib.sim_xmi_parser import (PopulateModelQuantities,
                                              TangoDeviceServer)

MODULE_LOGGER = logging.getLogger(__name__)


class Simdd_Parser(object):

    def __init__(self, simdd_json_file='/home/athanaseus/Desktop/SIMDD.json'):
        self.simdd_json_file = simdd_json_file
        self.device_attributes = {}
        self.device_commands = {}
        self.device_properties = {}
        self.parse_simdd_json_file()

    def parse_simdd_json_file(self):
        with open(self.simdd_json_file) as simdd_file:
            device_data = json.load(simdd_file)
        for data_component, elements in device_data.items():
            if data_component in ['dynamicAttributes']:
                attribute_info = self.get_device_data_components_dict(elements)
                self.device_attributes.update(attribute_info)
            elif data_component in ['commands']:
                command_info = self.get_device_data_components_dict(elements)
                self.device_commands.update(command_info)
            elif data_component in ['deviceProperties']:
                device_prop_info = self.get_device_data_components_dict(elements)
                self.device_properties.update(device_prop_info)

    def get_device_data_components_dict(self, elements):
        device_dict = dict()
        for attribute_data in elements:
            for attribute_info in attribute_data.values():
                name = attribute_info['name']
                device_dict[str(name)] = self.get_reformated_data(attribute_info)
        return device_dict

    def get_reformated_data(self, sim_device_info):
        def expand(key, value):
            if isinstance(value, dict):
                return [(k, v) for k, v in self.get_reformated_data(
                            value).items()]
            else:
                return [(str(key), str(value))]
        items = [map(str, item) for k, v in sim_device_info.items()
                 for item in expand(k, v)]
        return dict(items)

    def get_reformatted_device_attr_metadata(self):
        return self.device_attributes

    def get_reformatted_cmd_metadata(self):
        return self.device_commands

    def get_reformatted_properties_metadata(self):
        return self.device_properties


class SIMDD_PopulateModelQuantities(PopulateModelQuantities):

    def __init__(self, simdd_parser, sim_model_name, sim_model=None):
        self.xmi_parser = simdd_parser
        if not sim_model:
            self.sim_model = model.Model(sim_model_name)
        else:
            self.sim_model = sim_model
        self.setup_sim_quantities()


