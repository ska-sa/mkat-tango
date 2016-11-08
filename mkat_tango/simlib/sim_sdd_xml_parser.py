import os
import sys
import time
import weakref
import logging
import argparse

import xml.etree.ElementTree as ET


class SDD_Parser(object):
    """
    """
    def __init__(self):
        #self.sdd_xml_file = sdd_xml_file
        self.device_class_name = ""
        self.device_monitoring_points = []
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
        self.device_command_list = []
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
                self.device_command_list.append(self.extract_command_info(info))
            elif info.tag == 'MonitoringPointsList':
                self.device_monitoring_points.append(self.extract_monitoring_point_info(info))


    def extract_command_info(self, cmd_info):
        """
        """
        cmds = cmd_info.getchildren()
        for cmd in cmds:
            pass
            

    def extract_monitoring_point_info(self, mp_info):
        """
        """
        dev_mnt_pts = dict()
        monitoring_points = mp_info.getchildren()
        for mnt_pt in monitoring_points:
            attr = mnt_pt.attrib
            print mnt_pt
            print attr
            print attr['name']
            #print mnt_pt
            dev_mnt_pts_meta = dict()
            for prop in mnt_pt:
                if prop.text == None or prop.text.startswith('.'):
                    print "Property name: '%s' " % prop.tag
                    dev_mnt_pts_meta[prop.tag] = ''
                else:
                    print "Property name: '%s' | property val: '%s'" %(prop.tag, prop.text)
                    dev_mnt_pts_meta[prop.tag] = prop.text
                #print prop
            dev_mnt_pts[mnt_pt.attrib['name']] = dev_mnt_pts_meta
            print dev_mnt_pts
            print 6 * 'x'
