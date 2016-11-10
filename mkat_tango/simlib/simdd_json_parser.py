import os
import sys
import time
import logging

import json

MODULE_LOGGER = logging.getLogger(__name__)


class Simdd_Parser(object):

    def __init__(self, simdd_json_file):
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
                attribute_info = self.get_data_components_dict(elements)
                self.device_attributes.update(attribute_info)
            elif data_component in ['commands']:
                command_info = self.get_data_components_dict(elements)
                self.device_commands.update(command_info)
            elif data_component in ['deviceProperties']:
                device_prop_info = self.get_data_components_dict(elements)
                self.device_properties.update(device_prop_info)

    def get_data_components_dict(self, elements):
        device_dict = dict()
        for attribute_data in elements:
            for attribute_info in attribute_data.values():
                name = attribute_info['name']
                device_dict[str(name)] = attribute_info
        return device_dict
