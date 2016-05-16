#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""

    @author MeerKAT CAM team <cam@ska.ac.za>

"""
import logging

import PyTango

from katcp import Sensor
from katcp import server as katcp_server

from PyTango import CmdArgType, DevState, AttrDataFormat

from tango_inspecting_client import TangoInspectingClient

MODULE_LOGGER = logging.getLogger(__name__)

def tango_attr_descr2katcp_sensor(tango_attr_descr):
    """Convert a tango attribute description into an equivalent KATCP Sensor object

    Parameters
    ==========

    tango_attribute_descr : PyTango.AttributeInfoEx data structure

    Return Value
    ============
    sensor: katcp.Sensor object

    """
    sensor_type = None
    sensor_params = None

    if tango_attr_descr.data_format != AttrDataFormat.SCALAR:
        raise NotImplementedError("KATCP complexity with non-scalar data formats")

    if (tango_attr_descr.data_type == CmdArgType.DevDouble or
        tango_attr_descr.data_type == CmdArgType.DevFloat):
        sensor_type = Sensor.FLOAT
        if (tango_attr_descr.min_value != 'Not specified' or
            tango_attr_descr.max_value != 'Not specified'):
                sensor_params = [float(tango_attr_descr.min_value),
                                 float(tango_attr_descr.max_value)]
    elif (tango_attr_descr.data_type == CmdArgType.DevShort or
          tango_attr_descr.data_type == CmdArgType.DevLong or
          tango_attr_descr.data_type == CmdArgType.DevUShort or
          tango_attr_descr.data_type == CmdArgType.DevULong or
          tango_attr_descr.data_type == CmdArgType.DevLong64 or
          tango_attr_descr.data_type == CmdArgType.DevULong64):
              sensor_type = Sensor.INTEGER
              if (tango_attr_descr.min_value != 'Not specified' or
                  tango_attr_descr.max_value != 'Not specified'):
                  # TODO NM 16-05-2016: Should that not be 'and'?
                  sensor_params = [int(tango_attr_descr.min_value),
                                   int(tango_attr_descr.max_value)]
    elif tango_attr_descr.data_type == CmdArgType.DevBoolean:
        sensor_type = Sensor.BOOLEAN
    elif tango_attr_descr.data_type == CmdArgType.DevString:
        sensor_type = Sensor.STRING
    elif tango_attr_descr.data_type == CmdArgType.DevState:
        sensor_type = Sensor.DISCRETE
        state_enums = DevState.names
        state_possible_vals = state_enums.keys()
        sensor_params = state_possible_vals
    elif tango_attr_descr.data_type == CmdArgType.DevEnum:
        # TODO Should be DevEnum in Tango9. For now don't create sensor object
        #sensor_type = Sensor.DISCRETE
        #sensor_params = attr_name.enum_labels
        raise NotImplementedError("Cannot create DISCRETE sensors from the "
                                  "DevEnum attributes yet! Tango9 feature "
                                  "issue")
    else:
        raise NotImplementedError("Unhandled attribute type {!r}"
                                  .format(tango_attr_descr.data_type))


    return Sensor(sensor_type, tango_attr_descr.name,
                  tango_attr_descr.description,
                  tango_attr_descr.unit, sensor_params)

class TangoProxyDeviceServer(katcp_server.DeviceServer):
    def setup_sensors(self):
        pass

class TangoDevice2KatcpProxy(object):
    def __init__(self, katcp_server, tango_inspecting_client):
        self.katcp_server = katcp_server
        self.inspecting_client = tango_inspecting_client

    def start(self, timeout=None):
        self.inspecting_client.inspect()
        self.inspecting_client.tango_event_handler = self.update_sensor_values
        self.update_katcp_server_sensor_list()
        self.inspecting_client.setup_attribute_sampling()
        self.katcp_server.start(timeout=timeout)

    def stop(self):
        self.katcp_server.stop()

    def join(self, timeout=None):
        self.katcp_server.join(timeout=timeout)

    def update_katcp_server_sensor_list(self):
        tango_attr_descr = self.inspecting_client.device_attributes
        for attr_descr_name in tango_attr_descr.keys():
            try:
                sensor = tango_attr_descr2katcp_sensor(tango_attr_descr[attr_descr_name])
                self.katcp_server.add_sensor(sensor)
            except NotImplementedError as nierr:
                # Temporarily for unhandled attribute types
                MODULE_LOGGER.debug(str(nierr))
                
    def update_sensor_values(self, tango_event_data):
        attr_value = tango_event_data.attr_value
        name = getattr(attr_value, 'name', None)
        value = getattr(attr_value, 'value', None)
        timestamp = (attr_value.time.totime()
                     if hasattr(attr_value, 'time') else None)
        sensor = self.katcp_server.get_sensor(name)
        # TODO Might need to figure out how to map the AttrQuality values to the 
        # Sensor status constants
        sensor.set_value(value, timestamp=timestamp)
                
    @classmethod
    def from_addresses(cls, katcp_server_address, tango_device_address):
        tango_device_proxy = PyTango.DeviceProxy(tango_device_address)
        tango_inspecting_client = TangoInspectingClient(tango_device_proxy)
        katcp_host, katcp_port = katcp_server_address
        katcp_server = TangoProxyDeviceServer(katcp_host, katcp_port)
        katcp_server.set_concurrency_options(thread_safe=False, handler_thread=False)
        return cls(katcp_server, tango_inspecting_client)
