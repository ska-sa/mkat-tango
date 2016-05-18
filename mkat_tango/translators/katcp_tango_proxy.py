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
import sys

import PyTango

from katcp import Sensor
from katcp import server as katcp_server

from PyTango import DevState, AttrDataFormat, CmdArgType
from PyTango import (DevFloat, DevDouble, DevShort, DevLong, DevUShort, DevULong,
                     DevLong64, DevULong64, DevBoolean, DevString, DevEnum, DevUChar)

from tango_inspecting_client import TangoInspectingClient

MODULE_LOGGER = logging.getLogger(__name__)

_MIN_UCHAR_VALUE = 0
_MAX_UCHAR_VALUE = 255

def tango_attr_descr2katcp_sensor(attr_descr):
    """Convert a tango attribute description into an equivalent KATCP Sensor object

    Parameters
    ==========

    attr_descr : PyTango.AttributeInfoEx data structure

    Return Value
    ============
    sensor: katcp.Sensor object

    """
    sensor_type = None
    sensor_params = None

    if attr_descr.data_format != AttrDataFormat.SCALAR:
        raise NotImplementedError("KATCP complexity with non-scalar data formats")

    if (attr_descr.data_type == DevDouble or attr_descr.data_type == DevFloat):
        sensor_type = Sensor.FLOAT
        attr_min_val = attr_descr.min_value
        attr_max_val = attr_descr.max_value
        min_value = float('-inf') if attr_min_val == 'Not specified' else float(attr_min_val)
        max_value = float('inf') if attr_max_val == 'Not specified' else float(attr_max_val)
        sensor_params = [min_value, max_value]
    elif (attr_descr.data_type == DevShort or attr_descr.data_type == DevLong or
          attr_descr.data_type == DevUShort or attr_descr.data_type == DevULong or
          attr_descr.data_type == DevLong64 or attr_descr.data_type == DevULong64):
        sensor_type = Sensor.INTEGER
        attr_min_val = attr_descr.min_value
        attr_max_val = attr_descr.max_value
        min_value = -sys.maxint if attr_min_val == 'Not specified' else int(attr_min_val)
        max_value = sys.maxint if attr_max_val == 'Not specified' else int(attr_max_val)
        sensor_params = [min_value, max_value]
    elif attr_descr.data_type == DevUChar:
        sensor_type = Sensor.INTEGER
        sensor_params = [_MIN_UCHAR_VALUE, _MAX_UCHAR_VALUE]
    elif attr_descr.data_type == DevBoolean:
        sensor_type = Sensor.BOOLEAN
    elif attr_descr.data_type == DevString:
        sensor_type = Sensor.STRING
    elif attr_descr.data_type == CmdArgType.DevState:
        sensor_type = Sensor.DISCRETE
        state_enums = DevState.names
        state_possible_vals = state_enums.keys()
        sensor_params = state_possible_vals
    elif attr_descr.data_type == DevEnum:
        # TODO Should be DevEnum in Tango9. For now don't create sensor object
        #sensor_type = Sensor.DISCRETE
        #sensor_params = attr_name.enum_labels
        raise NotImplementedError("Cannot create DISCRETE sensors from the "
                                  "DevEnum attributes yet! Tango9 feature "
                                  "issue")
    else:
        raise NotImplementedError("Unhandled attribute type {!r}"
                                  .format(attr_descr.data_type))

    return Sensor(sensor_type, attr_descr.name, attr_descr.description,
                  attr_descr.unit, sensor_params)

class TangoProxyDeviceServer(katcp_server.DeviceServer):
    def setup_sensors(self):
        pass

class TangoDevice2KatcpProxy(object):
    def __init__(self, katcp_server, tango_inspecting_client):
        self.katcp_server = katcp_server
        self.inspecting_client = tango_inspecting_client

    def start(self, timeout=None):
        """Start the translator

        Starts the Tango client and the KATCP server with ioloop in another
        thread and subscibes to all Tango attributes for updates.

        For clean shutdown and thread cleanup, stop() needs to be called

        """
        self.inspecting_client.inspect()
        self.inspecting_client.sample_event_callback = self.update_sensor_values
        self.update_katcp_server_sensor_list()
        self.inspecting_client.setup_attribute_sampling()
        self.katcp_server.start(timeout=timeout)

    def stop(self):
        """Stop the translator

        At the moment only the KATCP component is stopped since we don't yet
        know how to stop the Tango DeviceProxy. Some thread leakage therefore to
        be expected :(

        """
        self.katcp_server.stop()
        # TODO NM 2016-05-17 Is it possible to stop a Tango DeviceProxy?

    def join(self, timeout=None):
        self.katcp_server.join(timeout=timeout)

    def update_katcp_server_sensor_list(self):
        """ Populate the dictionary of sensors in the KATCP device server
            instance with the corresponding TANGO device server attributes
        """
        tango_attr_descr = self.inspecting_client.device_attributes
        for attr_descr_name in tango_attr_descr.keys():
            try:
                sensor = tango_attr_descr2katcp_sensor(tango_attr_descr[attr_descr_name])
                self.katcp_server.add_sensor(sensor)
            except NotImplementedError as nierr:
                # Temporarily for unhandled attribute types
                MODULE_LOGGER.info(str(nierr), exc_info=True)

    def update_sensor_values(self, name, received_timestamp, timestamp, value,
                             quality, event_type):
        """Updates the KATCP sensor object's value accordingly with changes to
           its corresponding TANGO attribute's value.

        """
        try:
            sensor = self.katcp_server.get_sensor(name)
            # TODO Might need to figure out how to map the AttrQuality values to the
            # Sensor status constants
            sensor.set_value(value, timestamp=timestamp)
        except ValueError as verr:
            MODULE_LOGGER.info('Sensor not implemented yet!' + str(verr))

    @classmethod
    def from_addresses(cls, katcp_server_address, tango_device_address):
        """Instantiate TangoDevice2KatcpProxy from network addresses

        Parameters
        ==========
        katcp_server_address : tuple (hostname : str, port : int)
            Address where the KATCP server interface should listen
        tango_device_address : str
            Tango address for the device to be translated

        """
        tango_device_proxy = PyTango.DeviceProxy(tango_device_address)
        tango_inspecting_client = TangoInspectingClient(tango_device_proxy)
        katcp_host, katcp_port = katcp_server_address
        katcp_server = TangoProxyDeviceServer(katcp_host, katcp_port)
        katcp_server.set_concurrency_options(thread_safe=False, handler_thread=False)
        return cls(katcp_server, tango_inspecting_client)
