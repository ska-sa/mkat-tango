import xml.etree.ElementTree as ET

from PyTango import DevDouble, DevLong, DevBoolean, DevString
from mkat_tango.simlib import model

SDD_MP_PARAMS_TANGO_MAP = {
    'name': 'name',
    'Description': 'description',
    'DataType': 'data_type',
    'MinValue': 'min_value',
    'MaxValue': 'max_value',
    'RWType': 'writable'}

SDD_TYPES_TO_TANGO_TYPES = {
    'int': DevLong,
    'float': DevDouble,
    'boolean': DevBoolean,
    'string': DevString}

class SDD_Parser(object):
    """Parses the SDD xml file generated from DSL.

    Attributes
    ----------
    monitoring_points: dict

    commands: dict
    """
    def __init__(self):
        self.monitoring_points = {}
        self.commands = {}
        self._formatted_mnt_pts_info = {}

    def parse(self, sdd_xml_file):
        tree = ET.parse(sdd_xml_file)
        root = tree.getroot()
        self.commands.update(self.extract_command_info(root.find(
            'CommandList')))
        self.monitoring_points.update(self.extract_monitoring_point_info(
            root.find('MonitoringPointsList')))

        self._convert_mnt_pt_info()

    def extract_command_info(self, cmd_info):
        """Extracts all the information of the xml element 'CommandList'

        Parameters
        ----------
        cmd_info: xml.etree.ElementTree.Element
        e.g.
            <CommandList>
                <Command>
                    <CommandID></CommandID>
                    <CommandName>ON</CommandName>
                    <CommandDescription></CommandDescription>
                    <CommandType></CommandType>
                    <Timeout></Timeout>
                    <MaxRetry></MaxRetry>
                    <TimeForExecution></TimeForExecution>
                    <AvailableInModes>
                        <Mode></Mde>
                        <Mode></Mode>
                    </AvailableInModes>
                    <CommandParameters></CommandParameters>
                    <ResponseList>
                        <Response>
                            <ResponseID></ResponseID>
                            <ResponseName>RES_ON</ResponseName>
                            <ResponseType></ResponseType>
                            <ResponseParameters>
                                <Parameter>
                                    <ParameterID></ParameterID>
                                    <ParameterName>msg</ParameterName>
                                    <ParameterValue></ParameterValue>
                                </Parameter>
                            </ResponseParameters>
                        </Response>
                    </ResponseList>
                </Command>
            </CommandList>

        Returns
        -------
        cmds: dict
            A dictionary of all the commands and their metadata.
            e.g.
            {
                'cmd_name': {
                    'CommandID': '',
                    'Command_Name: '',
                    'CommandDescription: '',
                    'CommandType: '',
                    'Timeout': '',
                    'MaxRetry': '',
                    'TimeForExecution': '',
                    'AvailableInModes': {},
                    'CommandParameters': {},
                    'ResponseList': {
                        'response_name': {
                            'ResponseID': '',
                            'ResponseName': '',
                            'ResponseType': '',
                            'ResponseDescription': '',
                            'ResponseParameters': {
                                 'parameter_name': {
                                     'ParameterID': '',
                                     'ParameterName': '',
                                     'ParameterValue': '',
                                     }
                            }
                        }
                    }
                }
            }
        """
        cmds = {}
        commands = cmd_info.getchildren()
        for command in commands:
            cmd_metadata = {}
            for prop in command:
                cmd_metadata[prop.tag] = {}
                if prop.tag in ['CommandParameters']:
                    cmd_meta_prop = {}
                    for parameter in prop:
                        cmd_param_meta = {}
                        for parameter_prop in parameter:
                            cmd_param_meta[parameter_prop.tag] = (
                                parameter_prop.text)
                        cmd_meta_prop[cmd_param_meta['ParameterName']] = (
                            cmd_param_meta)
                    cmd_metadata[prop.tag].update(cmd_meta_prop)
                elif prop.tag in ['ResponseList']:
                    self._extract_response_list_info(cmd_metadata, prop)
                elif prop.tag in ['AvailableInModes']:
                    for prop_param in prop:
                        cmd_metadata[prop.tag][prop_param.tag] = prop_param.text
                else:
                    cmd_metadata[prop.tag] = prop.text
            cmds[cmd_metadata['CommandName']] = cmd_metadata
        return cmds

    def _extract_response_list_info(self, cmd_meta, prop):
        """Extracts the cmd response info from the command information
        and adds it to cmd_meta dictionary.

        Parameter
        ---------
        cmd_meta: dict
            A dictionary containing the extracted cmd metadata.

        prop: xml.etree.ElementTree.Element
            e.g.
            <ResponseList>
                <Response>
                    <ResponseID></ResponseID>
                    <ResponseName>RES_ON</ResponseName>
                    <ResponseType></ResponseType>
                    <ResponseParameters>
                        <Parameter>
                            <ParameterID></ParameterID>
                            <ParameterName>msg</ParameterName>
                            <ParameterValue></ParameterValue>
                        </Parameter>
                    </ResponseParameters>
                </Response>
            </ResponseList>

        Notes
        -----
        Adds the cmd response dictionary to the cmd meta dictionary.
            e.g.
            'ResponseList': {
                'response_name': {
                    'ResponseID': '',
                    'ResponseName': '',
                    'ResponseType': '',
                    'ResponseDescription': '',
                    'ResponseParameters': {
                        'parameter_name': {
                            'ParameterID': '',
                            'ParameterName': '',
                            'ParameterValue': '',
                        }
                    }
                }
            }
        """
        cmd_responses = {}      # To store a list of the cmd_responses
        for response in prop:
            cmd_response_meta = {}      # Stores the response properties
            for resp_prop in response:
                if resp_prop.tag in ['ResponseParameters']:
                    response_params = {}   # Stores the response paramaters
                    cmd_response_meta[resp_prop.tag] = {}
                    for parameter in resp_prop:
                        # Stores the properties of the parameter
                        resp_params_prop = {}
                        for parameter_prop in parameter:
                            resp_params_prop[parameter_prop.tag] =(
                                    parameter_prop.text)
                        response_params[resp_params_prop['ParameterName']] = (
                            resp_params_prop)
                        cmd_response_meta[resp_prop.tag].update(
                            response_params)
                else:
                    cmd_response_meta[resp_prop.tag] = resp_prop.text
            cmd_responses[cmd_response_meta['ResponseName']] = (
                        cmd_response_meta)

        cmd_meta[prop.tag].update(cmd_responses)

    def extract_monitoring_point_info(self, mp_info):
        """Extracts all the information of the xml element 'MonitoringPointsList'

        Parameters
        ----------
        mp_info: xml.etree.ElementTree.Element
            e.g.
            <MonitoringPointsList>
                <MonitoringPoint id="" name="Temperature" mandatory="TRUE/FALSE">
                    <Description></Description>
                    <DataType>float</DataType>
                    <Size>0</Size>
                    <RWType></RWType>
                    <PossibleValues>
                        <PossibleValue></PossibleValue>
                        <PossibleValue></PossibleValue>
                    </PossibleValues>
                    <ValueRange>
                        <MinValue>-10</MinValue>
                        <MaxValue>55</MaxValue>
                    </ValueRange>
                    <SamplingFrequency>
                        <DefaultValue></DefaultValue>
                        <MaxValue></MaxValue>
                    </SamplingFrequency>
                    <LoggingLevel></LoggingLevel>
                </MonitoringPoint>
            </MonitoringPointsList>

        Returns
        -------
        dev_mnt_pts: dict
            A dictionary of all the element's commands and their metadata.
            e.g.
            {
                'monitoring_pt_name': {
                    'id': '',
                    'name': '',
                    'Description': '',
                    'DataType': '',
                    'Size': '',
                    'RWType': '',
                    'PossibleValues': [],
                    'ValueRange': {
                        'MinValue': '',
                        'MaxValue': '',
                        },
                    'SamplingFrequecy': {
                        'DefaultValue': '',
                        'MaxValue': '',
                        }
                    'LoggingLevel' :''
                    }
            }
        """
        dev_mnt_pts = {}
        monitoring_points = mp_info.getchildren()
        for mnt_pt in monitoring_points:
            dev_mnt_pts_meta = {}
            dev_mnt_pts_meta['name'] = mnt_pt.attrib['name']
            dev_mnt_pts_meta['id'] = mnt_pt.attrib['id']
            for prop in mnt_pt:
                if prop.tag in ['ValueRange', 'SamplingFrequency']:
                    dev_mnt_pts_meta[prop.tag] = {}
                    for inner_prop in prop:
                        dev_mnt_pts_meta[prop.tag][inner_prop.tag] = (
                            inner_prop.text)
                elif prop.tag == "PossibleValues":
                    vals = []
                    for possible_val in prop:
                        vals.append(possible_val.text)
                    dev_mnt_pts_meta[prop.tag] = vals
                elif prop.tag == "DataType":
                    dev_mnt_pts_meta[prop.tag] = SDD_TYPES_TO_TANGO_TYPES[prop.text]
                else:
                    dev_mnt_pts_meta[prop.tag] = prop.text

            dev_mnt_pts[mnt_pt.attrib['name']] = dev_mnt_pts_meta
        return dev_mnt_pts

    def get_reformatted_device_attr_metadata(self):
        return self._formatted_mnt_pts_info

    def _convert_mnt_pt_info(self):
        """Converts the monitoring points data structure into a dictionary
        to make searching easier.

        A dictionary of all the element's monitoring points together with their
        metadata specified in the DSL generated xml file. The key
        represents the name of the monitoring point and the value is a dictionary
        of all the monitoring point's metadata.

            e.g.
            {
                'monitoring_pt_name': {
                    'id': '',
                    'name': '',
                    'description': '',
                    'data_type': '',
                    'size': '',
                    'writable': '',
                    'possiblevalues': [],
                    'min_value': '',
                    'max_value': '',
                    'samplingfrequecy': {
                        'DefaultValue': '',
                        'MaxValue': '',
                    },
                    'logginglevel' :''
                }
            }
        """
        monitoring_pts = {}
        for mpt_name, mpt_metadata in self.monitoring_points.items():
            monitoring_pts[mpt_name] = {}
            for metadata_prop_name, metadata_prop_val in mpt_metadata.items():
                # Unpack the min and max values from the ValueRange dictionary
                if metadata_prop_name == "ValueRange":
                    for extremity, extremity_val in metadata_prop_val.items():
                       monitoring_pts[mpt_name][SDD_MP_PARAMS_TANGO_MAP[extremity]] = (
                           extremity_val)
                else:
                    try:
                        monitoring_pts[mpt_name][SDD_MP_PARAMS_TANGO_MAP[metadata_prop_name]] = (
                            metadata_prop_val)
                    except KeyError:
                        monitoring_pts[mpt_name][metadata_prop_name.lower()] = metadata_prop_val
        self._formatted_mnt_pts_info =  monitoring_pts
