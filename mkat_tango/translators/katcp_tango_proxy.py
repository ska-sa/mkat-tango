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
import textwrap

import numpy as np
import tornado
import PyTango

from collections import namedtuple
from functools import partial

from tornado.gen import Return
from katcp import Sensor, kattypes
from katcp import server as katcp_server
from PyTango import DevState, AttrDataFormat, CmdArgType
from PyTango import (DevFloat, DevDouble,
                     DevUChar, DevShort, DevUShort, DevLong, DevULong,
                     DevLong64, DevULong64, DevBoolean, DevString, DevEnum)

from tango_inspecting_client import TangoInspectingClient

MODULE_LOGGER = logging.getLogger(__name__)

_MIN_UCHAR_VALUE = 0
_MAX_UCHAR_VALUE = 255

KATCP_REQUEST_DOC_TEMPLATE = (
"""?{desc.cmd_name} {desc.in_type} -> {desc.out_type}

Input Parameter
---------------

{in_type_desc}

Returns
-------

{out_type_desc}
"""
)

def dtype_params(dtype):
    try:
        info = np.iinfo(dtype)
    except ValueError:
        info = np.finfo(dtype)
    return (info.min, info.max)


KatcpTypeInfo = namedtuple('KatcpTypeInfo', ('KatcpType', 'sensor_type', 'params'))

TANGO_FLOAT_TYPES = set([DevFloat, DevDouble])
TANGO_INT_TYPES = set([DevUChar,DevShort, DevUShort, DevLong,
                       DevULong, DevLong64, DevULong64])
TANGO_NUMERIC_TYPES = TANGO_FLOAT_TYPES | TANGO_INT_TYPES
TANGO_CMDARGTYPE_NUM2NAME = {num: name
                             for name, num in PyTango.CmdArgType.names.items()}

TANGO2KATCP_TYPE_INFO = {
    DevFloat: KatcpTypeInfo(KatcpType=kattypes.Float, sensor_type=Sensor.FLOAT,
                            params=dtype_params(np.float32)),
    DevDouble: KatcpTypeInfo(KatcpType=kattypes.Float, sensor_type=Sensor.FLOAT,
                             params=dtype_params(np.float64)),
    DevUChar: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                            params=dtype_params(np.uint8)),
    DevShort: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                            params=dtype_params(np.int16)),
    DevUShort: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                             params=dtype_params(np.uint16)),
    DevLong: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                           params=dtype_params(np.int32)),
    DevULong: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                            params=dtype_params(np.uint32)),
    DevLong64: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                             params=dtype_params(np.int64)),
    DevULong64: KatcpTypeInfo(KatcpType=kattypes.Int, sensor_type=Sensor.INTEGER,
                              params=dtype_params(np.uint64)),
    DevBoolean: KatcpTypeInfo(KatcpType=kattypes.Bool, sensor_type=Sensor.BOOLEAN,
                              params=()),
    DevString: KatcpTypeInfo(KatcpType=kattypes.Str, sensor_type=Sensor.STRING,
                             params=()),
    DevEnum: KatcpTypeInfo(KatcpType=kattypes.Discrete, sensor_type=Sensor.DISCRETE,
                           params=())
}


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
        sensor_type = Sensor.DISCRETE
        sensor_params = attr_descr.enum_labels
    else:
        data_type_name = TANGO_CMDARGTYPE_NUM2NAME[attr_descr.data_type]
        raise NotImplementedError("Unhandled attribute type {!r}"
                                  .format(data_type_name))

    return Sensor(sensor_type, attr_descr.name, attr_descr.description,
                  attr_descr.unit, sensor_params)

def tango_cmd_descr2katcp_request(tango_command_descr, tango_device_proxy):
    """Convert a tango attribute description into an equivalent KATCP Sensor object

    Parameters
    ==========
    tango_command_descr : :class:`PyTango.CommandInfo` data structure
    tango_device_proxy : :class:`PyTango.DeviceProxy` instance
        When called, request_handler will use this tango device proxy to execute
        the command.

    Return Value
    ============
    request_handler: callable(katcp_server, katcp_req, katcp_msg)
        Request handler suitable for installing on a
        katcp.server.DeviceServer. Takes parameters
            katcp_server : katcp.server.DeviceServer instance
            katcp_req : katcp.server.ClientRequestConnection instance
            katcp_msg : katcp.Message request message instance
        returns katcp.Message reply message instance or a tornado Future that
        resolves with the same.

    Note
    ====
    The request_handler may do some type checking on the KATCP input arguments
    to ensure compatiblity with the Tango command that it is proxying.

    """
    in_kattype = tango_type2kattype_object(tango_command_descr.in_type)
    out_kattype = tango_type2kattype_object(tango_command_descr.out_type)
    cmd_name = tango_command_descr.cmd_name
    tango_request = partial(tango_device_proxy.command_inout,
                            green_mode=PyTango.GreenMode.Futures,
                            wait=False)

    request_args = [in_kattype] if in_kattype else []
    return_reply_args = [out_kattype] if out_kattype else []

    @kattypes.request(*request_args)
    @tornado.gen.coroutine
    def request_handler_with_input(server, req, input_param):
        # TODO docstring using stuff?
        # A reference for debugging ease so that it is in the closure
        tango_device_proxy
        tango_retval = yield tango_request(cmd_name, input_param)
        raise Return(
            ('ok', tango_retval) if tango_retval is not None else ('ok', ))

    @kattypes.request(*request_args)
    @tornado.gen.coroutine
    def request_handler_without_input(server, req):
        # A reference for debugging ease so that it is in the closure
        tango_device_proxy
        tango_retval = yield tango_request(cmd_name)
        raise Return(
            ('ok', tango_retval) if tango_retval is not None else ('ok', ))

    if in_kattype:
        handler = request_handler_with_input
        in_type_desc = tango_command_descr.in_type_desc
    else:
        handler = request_handler_without_input
        in_type_desc = 'Void'

    if out_kattype:
        out_type_desc = tango_command_descr.out_type_desc
    else:
        out_type_desc = 'Void'

    handler.__name__ = 'request_{}'.format(cmd_name)
    handler.__doc__ = KATCP_REQUEST_DOC_TEMPLATE.format(
        desc=tango_command_descr,
        in_type_desc=in_type_desc, out_type_desc=out_type_desc)
    return kattypes.return_reply(*return_reply_args)(handler)


def tango_type2kattype_object(tango_type):
    if tango_type == PyTango.DevVoid:
        return None
    try:
        katcp_type_info = TANGO2KATCP_TYPE_INFO[tango_type]
    except KeyError as ke:
        raise NotImplementedError("Tango wrapping not implemented for tango type {}"
                                  .format(tango_type))
    kattype_kwargs = {}
    if tango_type in TANGO_NUMERIC_TYPES:
        kattype_kwargs['min'], kattype_kwargs['max'] = katcp_type_info.params
    # TODO NM We should be able to handle the DevVar* variants by checking if
    # in_type.name starts with DevVar, and then lookup the 'scalar' type. The we
    # can just just multiple=True on the KATCP type
    return katcp_type_info.KatcpType(**kattype_kwargs)


class TangoProxyDeviceServer(katcp_server.DeviceServer):
    def setup_sensors(self):
        """Need a no-op setup_sensors() to satisfy superclass"""

    def add_request(self, request_name, handler):
        """Add a request handler to the internal list."""
        assert(handler.__doc__ is not None)
        self._request_handlers[request_name] = handler


class TangoDevice2KatcpProxy(object):
    def __init__(self, katcp_server, tango_inspecting_client):
        self.katcp_server = katcp_server
        self.inspecting_client = tango_inspecting_client

    def set_ioloop(self, ioloop=None):
        """Set the tornado IOLoop to use.

        Sets the tornado.ioloop.IOLoop instance to use, defaulting to
        IOLoop.current(). If set_ioloop() is never called the IOLoop is
        started in a new thread, and will be stopped if self.stop() is called.

        Notes
        -----
        Must be called before start() is called.

        """
        self.katcp_server.set_ioloop(ioloop)
        self.ioloop = self.katcp_server.ioloop

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
        self.update_katcp_server_request_list()
        return self.katcp_server.start(timeout=timeout)

    def stop(self, timeout=1.0):
        """Stop the translator

        At the moment only the KATCP component is stopped since we don't yet
        know how to stop the Tango DeviceProxy. Some thread leakage therefore to
        be expected :(

        """
        self.katcp_server.stop(timeout=timeout)
        self.inspecting_client.clear_attribute_sampling()
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

    def update_katcp_server_request_list(self):
        """ Populate the request handlers in  the KATCP device server
            instance with the corresponding TANGO device server commands
        """
        for cmd_name, cmd_info in self.inspecting_client.device_commands.items():
            try:
                req_handler = tango_cmd_descr2katcp_request(
                    cmd_info, self.inspecting_client.tango_dp)
            except NotImplementedError as exc:
                req_handler = self._dummy_request_handler_factory(
                    cmd_name, str(exc))

            self.katcp_server.add_request(cmd_name, req_handler)


    def _dummy_request_handler_factory(self, request_name, entrails):
        # Make a dummy request handler for tango commands that could not be
        # translated
        def request_dummy(self, req, msg):
            return ('fail', 'Untranslated command {}'.format(request_name))
        request_dummy = kattypes.return_reply(request_dummy)
        request_dummy.__doc__ = textwrap.dedent("""
        ?{} Untranslated tango command.

        Entrails below might provide some hint as to why this tango command
        could not be tanslated.

        {}""".lstrip()).format(request_name, entrails)

        return request_dummy

    def update_sensor_values(self, name, received_timestamp, timestamp, value,
                             quality, event_type):
        """Updates the KATCP sensor object's value accordingly with changes to
           its corresponding TANGO attribute's value.

        """
        try:
            sensor = self.katcp_server.get_sensor(name)
        except ValueError as verr:
            # AR 2016-05-19 TODO Need a robust way of dealing
            # with not implemented sensors
            MODULE_LOGGER.info('Sensor not implemented yet!' + str(verr))
        else:
            # KM 2016-05-18 TODO Might need to figure out how to map the
            # AttrQuality values to the sensor status constants
            if sensor.type == 'discrete':
                value = str(value)

            sensor.set_value(value, timestamp=timestamp)

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
