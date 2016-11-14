import xml.etree.ElementTree as ET

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
        self.monitoring_points = {}
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
        self.commands = {}
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
        self.commands.update(self.extract_command_info(root.find(
            'CommandList')))
        self.monitoring_points.update(self.extract_monitoring_point_info(
            root.find('MonitoringPointsList')))

    def extract_command_info(self, cmd_info):
        """
        """
        cmds = dict()
        commands = cmd_info.getchildren()
        for command in commands:
            cmd_meta = dict()
            for prop in command:
                cmd_meta[prop.tag] = {}
                if prop.tag in ['CommandParameters']:
                    cmd_meta_prop = {}
                    for parameter in prop:
                        cmd_meta_meta_meta = {}
                        for parameter_prop in parameter:
                            cmd_meta_meta_meta[parameter_prop.tag] = (
                                parameter_prop.text)
                        cmd_meta_prop[cmd_meta_meta_meta['ParameterName']] = (
                            cmd_meta_meta_meta)
                    cmd_meta[prop.tag].update(cmd_meta_prop)
                elif prop.tag in ['ResponseList']:
                    self._extract_response_list_info(cmd_meta, prop)
                elif prop.tag in ['AvailableInModes']:
                    for inner_prop in prop:
                        cmd_meta[prop.tag].update({inner_prop.tag:inner_prop.text})
                else:
                    cmd_meta[prop.tag] = prop.text
            cmds[cmd_meta['CommandName']] = cmd_meta
        return cmds

    def _extract_response_list_info(self, cmd_meta, prop):
        """
        """
        cmd_responses = {}      # To store a list of the cmd_responses
        for response in prop:
            cmd_response_meta = {}      # Stores the response properties
            for resp_prop in response:
                if resp_prop.tag in ['ResponseParameters']:
                    response_params = {}   # Stores the response paramaters
                    cmd_response_meta[resp_prop.tag] = {}
                    for parameter in resp_prop:
                        # Stores the properties of the paramter
                        resp_params_prop = {}
                        for parameter_prop in parameter:
                            resp_params_prop[parameter_prop.tag] =(
                                    parameter_prop.text)
                        response_params[resp_params_prop['ParameterName']] =(
                            resp_params_prop)
                        cmd_response_meta[resp_prop.tag].update(
                            response_params)
                else:
                    cmd_response_meta[resp_prop.tag] = resp_prop.text
            cmd_responses[cmd_response_meta['ResponseName']] =(
                        cmd_response_meta)

        cmd_meta[prop.tag].update(cmd_responses)

    def extract_monitoring_point_info(self, mp_info):
        """
        """
        dev_mnt_pts = dict()
        monitoring_points = mp_info.getchildren()
        for mnt_pt in monitoring_points:
            dev_mnt_pts_meta = {}
            dev_mnt_pts_meta['name'] = mnt_pt.attrib['name']
            for prop in mnt_pt:
                if prop.tag in ['ValueRange', 'SamplingFrequency']:
                    dev_mnt_pts_meta[prop.tag] = {}
                    for inner_prop in prop:
                        dev_mnt_pts_meta[prop.tag].update(
                                {inner_prop.tag: inner_prop.text})
                else:
                    dev_mnt_pts_meta[prop.tag] = prop.text

            dev_mnt_pts[mnt_pt.attrib['name']] = dev_mnt_pts_meta
        return dev_mnt_pts

    def get_reformatted_device_attr_metadata(self):
        """
        """
        monitoring_pts = {}
        for mpt_name, mpt_metadata in self.monitoring_points.items():
            monitoring_pts[mpt_name] = {}
            for metadata_prop_name, metadata_prop_val in mpt_metadata.items():
                if metadata_prop_name == "ValueRange":
                    for extremity, extremity_val in metadata_prop_val.items():
                       monitoring_pts[mpt_name].update(
                           {SDD_MP_PARAMS_TANGO_MAP[extremity] : extremity_val})
                    continue

                try:
                    monitoring_pts[mpt_name].update(
                        {SDD_MP_PARAMS_TANGO_MAP[metadata_prop_name] : metadata_prop_val})
                except KeyError:
                    monitoring_pts[mpt_name].update({metadata_prop_name : metadata_prop_val})
        return monitoring_pts
