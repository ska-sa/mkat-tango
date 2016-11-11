import os
import sys
import time
import weakref
import logging
import argparse

import xml.etree.ElementTree as ET

from mkat_tango import helper_module
from mkat_tango.simlib import quantities
from mkat_tango.simlib import model
from mkat_tango.simlib.sim_xmi_parser import PopulateModelQuantities

SDD_MP_PARAMS_TANGO_MAP = {
    'name': 'name',
    'Description': 'description',
    'DataType': 'data_type',
    'MinValue': 'min_value',
    'MaxValue': 'max_value',
    'RWType': 'writable'}

class SDD_Parser(object):
    """
    """
    def __init__(self):
        #self.sdd_xml_file = sdd_xml_file
        self.device_class_name = ""
        self.device_monitoring_points = {}
        """e.g.
            <MonitoringPoint id="" name="Temperature" mandatory="TRUE/FALSE">
                <Description>....</Description>
                <DataType>float</DataType>
                <Size>0</Size>
                <RWType>....</RWType>
                <PossibleValues></PossibleValues>
                <ValueRange>
                    <MinValue>-10</MinValue>
                    <MaxValue>55</MaxValue>
                </ValueRange>
                <SamplingFrequency>
                    <DefaultValue>....</DefaultValue>
                    <MaxValue>....</MaxValue>
                </SamplingFrequency>
                <LoggingLevel>....</LoggingLevel>
            </MonitoringPoint>

            to this ==>
            {
                'monitoring_pt_name': {
                    'id': '',
                    'name': '',
                    'mandatory': '',
                    'description': '',
                    'data_type': '',
                    'size': '',
                    'rwtype': '',
                    'values': [],
                    'min_value': '',
                    'max_value': '',
                    'sampling_frequecy': {
                        'default_value': '',
                        'max_value': '',
                        }
                    'logging_level' :''
                    }
        """
        self.device_commands = {}
        """e.g.
            <Command>
                <CommandID>....</CommandID>
                <CommandName>ON</CommandName>
                <CommandDescription>....</CommandDescription>
                <CommandType>....</CommandType>
                <Timeout>....</Timeout>
                <MaxRetry>....</MaxRetry>
                <TimeForExecution></TimeForExecution>
                <AvailableInModes>
                    <Mode>....</Mode>
                    <Mode>....</Mode>
                </AvailableInModes>
                <CommandParameters>....</CommandParameters>
                <ResponseList>
                    <Response>
                        <ResponseID>....</ResponseID>
                        <ResponseName>RES_ON</ResponseName>
                        <ResponseType>....</ResponseType>
                        <ResponseParameters>
                            <Parameter>
                                <ParameterID>....</ParameterID>
                                <ParameterName>msg</ParameterName>
                                <ParameterValue></ParameterValue>
                            </Parameter>
                        </ResponseParameters>
                    </Response>
                </ResponseList>
            </Command>

            to this ==>
            {
                'cmd_name': {
                    'cmd_id': '',
                    'cmd_name: '',
                    'cmd_description: '',
                    'cmd_type: '',
                    'time_out': '',
                    'max_retry': '',
                    'time_for_exec': '',
                    'modes': [],
                    'cmd_params': [],
                    'response_list': {
                        'response': {
                            'resp_id': '',
                            'resp_name': '',
                            'resp_type': '',
                            'resp_description': '',
                            'resp_params': {
                                 'param': {
                                     'param_id': '',
                                     'param_name': '',
                                     'param_val': '',
                                     }
                            }
                        }
                    }
                }
            }
        """

    def parse(self, sdd_xml_file):
        """
        """
        tree = ET.parse(sdd_xml_file)
        root = tree.getroot()

        main_element_info = root.getchildren()

        for info in main_element_info:
            if info.tag == 'CommandList':
                self.device_commands.update(self.extract_command_info(info))
            elif info.tag == 'MonitoringPointsList':
                self.device_monitoring_points.update(
                    self.extract_monitoring_point_info(info))


    def extract_command_info(self, cmd_info):
        """
        """
        cmds_s = dict()
        cmds = cmd_info.getchildren()
        for cmd in cmds:
            cmd_meta = dict()
            for prop in cmd:
                cmd_meta[prop.tag] = {}
                if prop.tag in ['CommandParameters']:
                    cmd_meta_meta = {}
                    for parameter in prop:
                        cmd_meta_meta_meta = {}
                        for parameter_prop in parameter:
                            if (parameter_prop.text == None or
                                    parameter_prop.text.startswith('.')):
                                cmd_meta_meta_meta[parameter_prop.tag] = ''
                            else:
                                cmd_meta_meta_meta[parameter_prop.tag] = (
                                    parameter_prop.text)
                        cmd_meta_meta[cmd_meta_meta_meta['ParameterName']] = (
                            cmd_meta_meta_meta)
                    cmd_meta[prop.tag].update(cmd_meta_meta)
                elif prop.tag in ['ResponseList']:
                    cmd_responses = {}      # To store a list of the cmd_responses
                    for response in prop:
                        #print "RES '%s'" % response.tag
                        cmd_response_meta = {}      # Stores the response properties
                        for resp_prop in response:
                            if resp_prop.tag in ['ResponseParameters']:
                                response_params = {}   # Stores the response paramaters
                                cmd_response_meta[resp_prop.tag] = {}
                                for parameter in resp_prop:
                                    # Stores the properties of the paramter
                                    resp_params_prop = {}
                                    for parameter_prop in parameter:
                                        if (parameter_prop.text == None or
                                                parameter_prop.text.startswith('.')):
                                            resp_params_prop[parameter_prop.tag] = ''
                                        else:
                                            resp_params_prop[parameter_prop.tag] =(
                                                parameter_prop.text)

                                    response_params[resp_params_prop['ParameterName']] =(
                                        resp_params_prop)
                                    cmd_response_meta[resp_prop.tag].update(
                                        response_params)

                            elif (resp_prop.text == None or
                                  resp_prop.text.startswith('.')):
                                cmd_response_meta[resp_prop.tag] = ''
                            else:
                                cmd_response_meta[resp_prop.tag] = resp_prop.text
                        cmd_responses[cmd_response_meta['ResponseName']] =(
                            cmd_response_meta)

                    cmd_meta[prop.tag].update(cmd_responses)
                elif prop.tag in ['AvailableInModes']:
                    for inner_prop in prop:
                        if inner_prop.text == None or inner_prop.text.startswith('.'):
                            cmd_meta[prop.tag].update({inner_prop.tag: ''})
                        else:
                            cmd_meta[prop.tag].update(
                                {inner_prop.tag: inner_prop.text})
                elif prop.text == None or prop.text.startswith('.'):
                    cmd_meta[prop.tag] = ''
                else:
                    cmd_meta[prop.tag] = prop.text
            cmds_s[cmd_meta['CommandName']] = cmd_meta
        return cmds_s

    # WIP (KM 12-11-2016)  to refactor the above method  
    def extract_cmd_info(self, cmd_info):
        dev_cmds = dict()
        cmd_list = cmd_info.findall('Command')
        for cmd in cmd_list:
            print cmd.tag
            cmd_meta = {}
            cmd_meta['name'] = cmd.find('CommandName').text
            for props in cmd:
                print "Parent prop '%s'" %props.tag
                if props.getchildren() == []:
                    val = ('' if props.text == None or props.text.startswith('.')
                           else props.text)
                    cmd_meta[props.tag] = val
                else:
                    cmd_meta[props.tag] = {}
                    els = props.getchildren()
                    for child in els:
                        print "Child prop '%s'" %child.tag
                        ele_meta = self._unpack_parent(child)
                        if type(ele_meta) == dict:
                            cmd_meta[props.tag].update(ele_meta)
                        while(type(ele_meta) != dict):
                            print "Element to unpack '%s' " %ele_meta
                            if type(ele_meta) == dict:
                                dev_cmds[cmd.tag].update(ele_meta)
                            else:
                                dev_cmds[cmd.tag].update({ele_meta.tag:{}})
                                ele_meta = self._unpack_parent(ele_meta)
            print dev_cmds
            dev_cmds[cmd_meta['name']] = cmd_meta
        return dev_cmds
    # WIP (KM 12-11-2016) to make it recursively extract info from deeply nested tags
    def extract_monitoring_point_info(self, mp_info):
        dev_mnt_pts = dict()
        mnt_pt_list = mp_info.findall('MonitoringPoint')
        for mp in mnt_pt_list:
            dev_mnt_pts_meta = {}
            dev_mnt_pts_meta['name'] = mp.attrib['name']
            for props in mp:
                if props.getchildren() == []:
                    val = ('' if props.text == None or props.text.startswith('.')
                        else props.text)
                    dev_mnt_pts_meta[props.tag] = val
                else:
                    dev_mnt_pts_meta[props.tag] = {}
                    els = props.getchildren()
                    for child in els:
                        ele_meta = self._unpack_parent(child)
                        if type(ele_meta) == dict:
                            dev_mnt_pts_meta[props.tag].update(ele_meta)
                        while(type(ele_meta) != dict):
                            if type(ele_meta) == dict:
                                dev_mnt_pts[mp.tag].update(ele_meta)
                            else:
                                dev_mnt_pts[mp.tag].update({ele_meta.tag : {}})
                                ele_meta = self._unpack_parent(ele_meta) 
            dev_mnt_pts[dev_mnt_pts_meta['name']] = dev_mnt_pts_meta
        return dev_mnt_pts


    def _unpack_parent(self, element):
        if element.getchildren() == []:
            val = element.text
            if val == None or val.startswith('.'):
                val = ''
            return {element.tag:val}
        else:
            return element.getchildren()


    def get_reformatted_device_attr_metadata(self):
        """
        """
        monitoring_pts = {}
        for mpt_name, mpt_metadata in self.device_monitoring_points.items():
            monitoring_pts[mpt_name] = {}
            for metadata_prop_name, metadata_prop_val in mpt_metadata.items():
                if metadata_prop_name == "ValueRange":
                    for extremity, extremity_val in metadata_prop_val.items():
                       monitoring_pts[mpt_name].update(
                           {SDD_MP_PARAMS_TANGO_MAP[extremity] : extremity_val})
                    break

                try:
                    monitoring_pts[mpt_name].update(
                        {SDD_MP_PARAMS_TANGO_MAP[metadata_prop_name] : metadata_prop_val})
                except KeyError:
                    monitoring_pts[mpt_name].update({metadata_prop_name : metadata_prop_val})
        return monitoring_pts



class SDD_PopulateModelQuantities(PopulateModelQuantities):
    """
    """
    def __init__(self, sdd_parser, sim_model_name, sim_model=None):
        self.xmi_parser = sdd_parser
        if not sim_model:
            self.sim_model = model.Model(sim_model_name)
        else:
            self.sim_model = sim_model

        self.setup_sim_quantities()
