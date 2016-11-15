import os
import sys
import time
import logging

import json

from PyTango import DevState, DevDouble, DevString, DevBoolean
from PyTango._PyTango import CmdArgType

MODULE_LOGGER = logging.getLogger(__name__)


class Simdd_Parser(object):

    def __init__(self, simdd_json_file):
        # Simulator decription datafile in json format
        self.simdd_json_file = simdd_json_file
        self.device_attributes = {}
        """The Data structure format is a dict containing attribute info in a dict

        e.g.
        {'temperature': {
            'abs_change': '0.5',
            'archive_abs_change': '0.5',
            'archive_period': '1000',
            'archive_rel_change': '10',
            'data_format': '',
            'data_type': PyTango._PyTango.CmdArgType.DevDouble,
            'delta_t': '1000',
            'delta_val': '0.5',
            'description': 'Current temperature outside near the telescope.',
            'display_level': 'OPERATOR',
            'event_period': '1000',
            'label': 'Outside Temperature',
            'max_alarm': '50',
            'max_bound': '50',
            'max_dim_x': '1',
            'max_dim_y': '0',
            'max_slew_rate': '1',
            'max_value': '51',
            'mean': '25',
            'min_alarm': '-9',
            'min_bound': '-10',
            'min_value': '-10',
            'name': 'temperature',
            'period': '1000',
            'rel_change': '10',
            'unit': 'Degrees Centrigrade',
            'update_period': '1',
            'writable': 'READ'},
        }

        """
        self.device_commands = {}
        """
        The Data structure format is a dict containing command info in a dict

        e.g.
        {'On': {
            'description': 'Turns On Device',
            'dformat_in': '',
            'dformat_out': '',
            'doc_in': 'No input parameter',
            'doc_out': 'Command responds',
            'dtype_in': 'Void',
            'dtype_out': 'String',
            'name': 'On'},
        }

        """
        self.device_properties = {}
        """
        Data structure format is a list containing device property info in a dict

        e.g.
        {'sim_data_description_file': {
            'default_value': '',
            'name': 'sim_data_description_file',
            'type': 'string'},
        }

        """
        self.parse_simdd_json_file()

    def parse_simdd_json_file(self):
        """
        Read simulator description data from json file into `self.device_properties`

        Stores all the simulator description data from the json file into
        appropriate attribute, command and device property data structures.
        Loops through the json object elements and updates description
        information of dynamic/attributes into `self.device_attributes`,
        commands into `self.device_commands`, and device_properties into
        `self.device_properties`.

        Notes
        =====
        - Data structures, are type dict with dictionary elements keyed with
          element name and values must be the corresponding data value.

        """
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
        """
        Extract description data from the simdd json element

        Parameters
        ----------

        elements: list
            List of device data elements with items in unicode format
        e.g.
        [{
            "basicAttributeData": {
                "name": "temperature",
                "unit": "Degrees Centrigrade",
                "label": "Outside Temperature",
                "description": "Current temperature outside near the telescope.",
                "data_type": "Double",
                "data_format": "",
                "delta_t": "1000",
                "delta_val": "0.5",
                "data_shape": {
                    "max_dim_x": "1",
                    "max_dim_y": "0"
                },
                "attributeErrorChecking": {
                    "min_value": "-10",
                    "max_value": "51",
                    "min_alarm": "-9",
                    "max_alarm": "50"
                },
                "attributeInterlocks": {
                    "writable": "READ"
                },
                "dataSimulationParameters": {
                    "randomlyVaryingNumber": {
                        "min_bound": "-10",
                        "max_bound": "50",
                        "mean": "25",
                        "max_slew_rate": "1",
                        "update_period": "1"
                    }
                },
                "attributeControlSystem": {
                    "display_level": "OPERATOR",
                    "period": "1000",
                    "EventSettings": {
                        "eventArchiveCriteria": {
                            "archive_abs_change": "0.5",
                            "archive_period": "1000",
                            "archive_rel_change": "10"
                        },
                        "eventCrateria": {
                            "abs_change": "0.5",
                            "event_period": "1000",
                            "rel_change": "10"
                        }
                    }
                }
            }
        }]

        Returns
        -------
            device_dict: dict
                device data dictionary in the format of
                `self.device_attributes` or `self.device_commands`
        """
        device_dict = dict()
        for attribute_data in elements:
            for attribute_info in attribute_data.values():
                name = attribute_info['name']
                device_dict[str(name)] = self.get_reformated_data(attribute_info)
        return device_dict

    def get_reformated_data(self, sim_device_info):
        """Helper function for flattening the data dicts to be more readable

        Parameters
        ----------
        sim_device_info: dict
            Data element Dict
        e.g.
        {"basicAttributeData": {
                "name": "temperature",
                "unit": "Degrees Centrigrade",
                "label": "Outside Temperature",
                "description": "Current temperature outside near the telescope.",
                "data_type": "Double",
                "data_format": "",
                "delta_t": "1000",
                "delta_val": "0.5",
                "data_shape": {
                    "max_dim_x": "1",
                    "max_dim_y": "0"
                },
                "attributeErrorChecking": {
                    "min_value": "-10",
                    "max_value": "51",
                    "min_alarm": "-9",
                    "max_alarm": "50"
                },
                "attributeInterlocks": {
                    "writable": "READ"
                },
                "dataSimulationParameters": {
                    "randomlyVaryingNumber": {
                        "min_bound": "-10",
                        "max_bound": "50",
                        "mean": "25",
                        "max_slew_rate": "1",
                        "update_period": "1"
                    }
                },
                "attributeControlSystem": {
                    "display_level": "OPERATOR",
                    "period": "1000",
                    "EventSettings": {
                        "eventArchiveCriteria": {
                            "archive_abs_change": "0.5",
                            "archive_period": "1000",
                            "archive_rel_change": "10"
                        },
                        "eventCrateria": {
                            "abs_change": "0.5",
                            "event_period": "1000",
                            "rel_change": "10"
                        }
                    }
                }
            }
        }

        Return
        ------
        items : dict
            A more formatted and easy to read dictionary
        e.g.

        {
            'abs_change': '0.5',
            'archive_abs_change': '0.5',
            'archive_period': '1000',
            'archive_rel_change': '10',
            'data_format': '',
            'data_type': PyTango._PyTango.CmdArgType.DevDouble,
            'delta_t': '1000',
            'delta_val': '0.5',
            'description': 'Current temperature outside near the telescope.',
            'display_level': 'OPERATOR',
            'event_period': '1000',
            'label': 'Outside Temperature',
            'max_alarm': '50',
            'max_bound': '50',
            'max_dim_x': '1',
            'max_dim_y': '0',
            'max_slew_rate': '1',
            'max_value': '51',
            'mean': '25',
            'min_alarm': '-9',
            'min_bound': '-10',
            'min_value': '-10',
            'name': 'temperature',
            'period': '1000',
            'rel_change': '10',
            'unit': 'Degrees Centrigrade',
            'update_period': '1',
            'writable': 'READ'
        }
        """
        def expand(key, value):
            """Method to expand values of a value if it is an instance of dict"""
            if isinstance(value, dict):
                # Recursively call get_reformated_data if value is still a dict
                return [(param_name, param_val)
                        for param_name, param_val in self.get_reformated_data(
                        value).items()]
            else:
                # Since the data type specified in the SIMDD is a string format
                # e.g. Double, it is require in Tango device as a CmdArgType
                # i.e. PyTango._PyTango.CmdArgType.DevDouble
                return [(str(key), eval(str(getattr(CmdArgType, "Dev%s" % value)))
                        if str(key) in ['data_type'] else str(value))]
        items = [item for param_name, param_val in sim_device_info.items()
                 for item in expand(param_name, param_val)]
        return dict(items)  # Format the output item list of tuples as a dictionary

    def get_reformatted_device_attr_metadata(self):
        """Returns a more formatted attribute data structure in a format of dict"""
        return self.device_attributes

    def get_reformatted_cmd_metadata(self):
        """Returns a more formatted command data structure in a format of dict"""
        return self.device_commands

    def get_reformatted_properties_metadata(self):
        """Returns a more formatted device prop data structure in a format of dict"""
        return self.device_properties
