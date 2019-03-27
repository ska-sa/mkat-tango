#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""

    @author MeerKAT CAM team <cam@ska.ac.za>

"""
import logging
import textwrap
import time

import numpy as np
import tornado
import tango

from collections import namedtuple
from functools import partial

from tornado.gen import Return
from katcp import Sensor, kattypes, Message
from katcp import server as katcp_server
from katcp.server import BASE_REQUESTS
from tango import DevState, AttrDataFormat, CmdArgType
from tango import (DevFloat, DevDouble,AttrQuality,
                     DevUChar, DevShort, DevUShort, DevLong, DevULong,
                     DevLong64, DevULong64, DevBoolean, DevString, DevEnum)

from mkat_tango.translators.utilities import tangoname2katcpname
from mkat_tango.translators.tango_inspecting_client import TangoInspectingClient

log = logging.getLogger("mkat_tango.translators.katcp_tango_proxy")

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
TANGO_INT_TYPES = set([DevUChar, DevShort, DevUShort, DevLong,
                       DevULong, DevLong64, DevULong64])
TANGO_NUMERIC_TYPES = TANGO_FLOAT_TYPES | TANGO_INT_TYPES
TANGO_CMDARGTYPE_NUM2NAME = {num: name
                             for name, num in tango.CmdArgType.names.items()}


class TangoStateDiscrete(kattypes.Discrete):
    """A kattype that is compatible with the tango.DevState enumeration"""

    def check(self, value, major):
        return super(TangoStateDiscrete, self).check(str(value), major)

    def encode(self, value, major):
        return super(TangoStateDiscrete, self).encode(str(value), major)

    def decode(self, value, major):
        return getattr(tango.DevState, value)

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
                           params=()),
    CmdArgType.DevState: KatcpTypeInfo(
        KatcpType=TangoStateDiscrete, sensor_type=Sensor.DISCRETE,
        params=(DevState.names.keys()))
}


TANGO_ATTRIBUTE_QUALITY_TO_KATCP_SENSOR_STATUS = {
        AttrQuality.ATTR_VALID: Sensor.NOMINAL,
        AttrQuality.ATTR_WARNING: Sensor.WARN,
        AttrQuality.ATTR_ALARM: Sensor.ERROR,
        AttrQuality.ATTR_INVALID: Sensor.FAILURE
}

def tango_attr_descr2katcp_sensors(attr_descr):
    """Convert a tango attribute description into an equivalent KATCP Sensor object(s)

    Parameters
    ==========

    attr_descr : tango.AttributeInfoEx data structure

    Return Value
    ============
    list: A list of katcp.Sensor objects.

    """
    sensor_type = None
    sensor_params = None

    if (attr_descr.data_format != AttrDataFormat.SCALAR and
        attr_descr.data_format != AttrDataFormat.SPECTRUM):
        raise NotImplementedError(
            "KATCP complexity with non-scalar/spectrum data formats")

    try:
        katcp_type_info = TANGO2KATCP_TYPE_INFO[attr_descr.data_type]
    except KeyError:
        data_type_name = TANGO_CMDARGTYPE_NUM2NAME[attr_descr.data_type]
        raise NotImplementedError("Unhandled attribute type {!r}"
                                  .format(data_type_name))

    sensor_type = katcp_type_info.sensor_type
    attr_min_val = attr_descr.min_value
    attr_max_val = attr_descr.max_value

    sensors = []

    for index in range(attr_descr.max_dim_x):
        if attr_descr.data_type in TANGO_INT_TYPES:
            min_value = (katcp_type_info.params[0]
                     if attr_min_val == 'Not specified' else int(attr_min_val))
            max_value = (katcp_type_info.params[1]
                     if attr_max_val == 'Not specified' else int(attr_max_val))
            sensor_params = [min_value, max_value]
        elif attr_descr.data_type in TANGO_FLOAT_TYPES:
            min_value = (katcp_type_info.params[0]
                     if attr_min_val == 'Not specified' else float(attr_min_val))
            max_value = (katcp_type_info.params[1]
                     if attr_max_val == 'Not specified' else float(attr_max_val))
            sensor_params = [min_value, max_value]
        elif attr_descr.data_type == DevEnum:
            sensor_params = attr_descr.enum_labels
        elif attr_descr.data_type == CmdArgType.DevState:
            sensor_params = katcp_type_info.params

        if attr_descr.data_format == AttrDataFormat.SPECTRUM:
            sensor_name = attr_descr.name + "." + str(index)
        else:
            sensor_name = attr_descr.name

        sensors.append(Sensor(sensor_type, sensor_name, attr_descr.description,
                              attr_descr.unit, sensor_params))

    return sensors

def tango_cmd_descr2katcp_request(tango_command_descr, tango_device_proxy):
    """Convert tango command description to equivalent KATCP reply handler

    Parameters
    ==========
    tango_command_descr : :class:`tango.CommandInfo` data structure
    tango_device_proxy : :class:`tango.DeviceProxy` instance
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
                            green_mode=tango.GreenMode.Futures,
                            wait=False)

    request_args = [in_kattype] if in_kattype else []
    return_reply_args = [out_kattype] if out_kattype else []

    # We need to create handlers with different signatures depending on whether
    # the tango command takes an input parameter or not

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
    def request_handler_with_array_input(server, req, *input_param):
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
        if 'Array' in str(tango_command_descr.in_type):
            handler = request_handler_with_array_input
        else:
            handler = request_handler_with_input
        in_type_desc = tango_command_descr.in_type_desc
    else:
        handler = request_handler_without_input
        # Fill in 'Void' as input description for commands that do not take
        # an input value so that the KATCP docstring makes sense
        in_type_desc = 'Void'

    if out_kattype:
        out_type_desc = tango_command_descr.out_type_desc
    else:
        # Fill in 'Void' as output description for commands that do not produce
        # an output value so that the KATCP docstring makes sense
        out_type_desc = 'Void'

    handler.__name__ = 'request_{}'.format(cmd_name)
    # Format the KATCP docstring template with the info of this particular
    # command
    handler.__doc__ = KATCP_REQUEST_DOC_TEMPLATE.format(
        desc=tango_command_descr,
        in_type_desc=in_type_desc, out_type_desc=out_type_desc)
    return kattypes.return_reply(*return_reply_args)(handler)


def tango_type2kattype_object(tango_type):
    """Convert Tango type object to corresponding kattype type object

    Input Parameters
    ----------------

    tango_type : `Pytango.CmdArgType` enum
        Tango type to translate, e.g. tango.CmdArgType.DevFloat

    Returns
    -------

    kattype_object : `katcp.kattypes.KatcpType` subclass
        KATCP type object equivalent to the input tango type. E.g. input of
        DevUChar will return a kattypes.Int object with min=0 and max=255,
        matching the min/max values of the corresponing tango type.

    """
    kattype_kwargs = {}
    if tango_type == tango.DevVoid:
        return None
    try:
        if 'Array' in str(tango_type):
            kattype_kwargs['multiple'] = True
            tango_type = getattr(tango, str(tango_type).replace('Array', '')
                                 .replace('Var', ''), None)
        katcp_type_info = TANGO2KATCP_TYPE_INFO[tango_type]
    except KeyError as ke:
        raise NotImplementedError("Tango wrapping not implemented for tango type {}"
                                  .format(tango_type))
    if tango_type in TANGO_NUMERIC_TYPES:
        kattype_kwargs['min'], kattype_kwargs['max'] = katcp_type_info.params
    elif tango_type == CmdArgType.DevState:
        # TODO (NM, KM) 2016-05-30 can we get rid of this if statement by using
        # TANGO2KATCP_TYPE_INFO better?
        kattype_kwargs = [name for name in katcp_type_info.params]
        return katcp_type_info.KatcpType(kattype_kwargs)
    return katcp_type_info.KatcpType(**kattype_kwargs)

def is_tango_device_running(tango_device_proxy, logger=log):
    """Checks if the TANGO device server is running.

    Input Parameters
    ----------------

    tango_device_proxy : tango.DeviceProxy instance

    Returns
    -------

    is_device_running : boolean

    """
    try:
        tango_device_proxy.ping()
    except tango.DevFailed as deverr:
        deverr_reasons = set([arg.reason for arg in deverr.args])
        deverr_desc = set([arg.desc for arg in deverr.args])
        for reason, description in zip(deverr_reasons, deverr_desc):
            logger.error("{} : {}".format(reason, description))
        is_device_running = False
    else:
        is_device_running = True

    return is_device_running


class TangoProxyDeviceServer(katcp_server.DeviceServer):
    def setup_sensors(self):
        """Need a no-op setup_sensors() to satisfy superclass"""

    def get_sensor_list(self):
        return self._sensors.keys()

    def get_requests(self):
        return self._request_handlers.keys()

    def add_request(self, request_name, handler):
        """Add a request handler to the internal list."""
        assert(handler.__doc__ is not None)
        self._request_handlers[request_name] = handler
        setattr(self, 'request_{}'.format(request_name), handler)

    def remove_request(self, request_name):
        """Remove a request handler from the internal list."""
        if request_name not in BASE_REQUESTS:
            del(self._request_handlers[request_name])
            delattr(self, 'request_{}'.format(request_name))


class TangoDevice2KatcpProxy(object):
    def __init__(self, katcp_server, tango_inspecting_client, logger=log):
        self.katcp_server = katcp_server
        self.inspecting_client = tango_inspecting_client
        self._logger = logger

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
        tango_device_proxy = self.inspecting_client.tango_dp
        if not is_tango_device_running(tango_device_proxy, logger=self._logger):
            self.wait_for_device(tango_device_proxy)
        self._logger.info("Connection to the device server established")
        self.inspecting_client.inspect()
        self.inspecting_client.sample_event_callback = self.update_sensor_values
        self.inspecting_client.interface_change_callback = (
            self.update_request_sensor_list)
        self.update_katcp_server_sensor_list(self.inspecting_client.device_attributes)
        self.update_katcp_server_request_list(self.inspecting_client.device_commands)
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

    def update_request_sensor_list(self, device_name, received_timestamp,
                                   attributes, commands):
        self.update_katcp_server_sensor_list(attributes)
        self.update_katcp_server_request_list(commands)
        self.katcp_server.mass_inform(Message.inform('interface-changed'))

    def update_katcp_server_sensor_list(self, attributes):
        """ Populate the dictionary of sensors in the KATCP device server
            instance with the corresponding TANGO device server attributes
        """
        sensors = self.katcp_server.get_sensor_list()
        tango2katcp_sensors = []
        sensor_attribute_map = {}

        for attribute_name, attribute_config in attributes.items():
            if attribute_name == "AttributesNotAdded":
                self._logger.debug(
                    "Skipping creation of sensor objects for attribute %s.",
                    attribute_name)
                continue
            sensor_name = tangoname2katcpname(attribute_name)
            # This is to handle the mapping of the spectrum type attribute name with its
            # decomposition into multiple sensor names. It will ensure that we add/remove
            # the correct sensors from the KATCP server.
            if attribute_config.data_format == AttrDataFormat.SPECTRUM:
                sensors_ = []
                for sensor in sensors:
                    if sensor.startswith(sensor_name + '.'):
                        sensors_.append(sensor)

                if len(sensors_) - attribute_config.max_dim_x == 0:
                    tango2katcp_sensors.extend(sensors_)
                else:
                    tango2katcp_sensors.append(sensor_name)

                sensor_attribute_map[sensor_name] = attribute_config
                continue

            tango2katcp_sensors.append(sensor_name)
            sensor_attribute_map[sensor_name] = attribute_config

        sensors_to_remove = list(set(sensors) - set(tango2katcp_sensors))
        sensors_to_add = list(set(tango2katcp_sensors) - set(sensors))

        for sensor_name in sensors_to_remove:
            self.katcp_server.remove_sensor(sensor_name)

        for sensor_name in sensors_to_add:
            try:
                sensors = tango_attr_descr2katcp_sensors(
                    sensor_attribute_map[sensor_name])
                for sensor in sensors:
                    self.katcp_server.add_sensor(sensor)
            except NotImplementedError as nierr:
                # Temporarily for unhandled attribute types
                self._logger.debug(str(nierr), exc_info=True)

        new_attributes = [sensor_attribute_map[sensor].name for sensor in sensors_to_add]
        lower_case_attributes = map(lambda attr_name:attr_name.lower(), new_attributes)
        orig_attr_names_map = dict(zip(lower_case_attributes, new_attributes))
        self.inspecting_client.orig_attr_names_map.update(orig_attr_names_map)
        self.inspecting_client.setup_attribute_sampling(new_attributes)

    def update_katcp_server_request_list(self, commands):
        """ Populate the request handlers in  the KATCP device server
            instance with the corresponding TANGO device server commands
        """
        requests = self.katcp_server.get_requests()
        requests_to_remove = list(set(requests) - set(commands))
        requests_to_add = list(set(commands) - set(requests))

        for request_name in requests_to_remove:
            self.katcp_server.remove_request(request_name)

        for request_name in requests_to_add:
            try:
                req_handler = tango_cmd_descr2katcp_request(
                    commands[request_name], self.inspecting_client.tango_dp)
            except NotImplementedError as exc:
                req_handler = self._dummy_request_handler_factory(
                    request_name, str(exc))

            self.katcp_server.add_request(request_name, req_handler)

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
        if name == "AttributesNotAdded":
            self._logger.debug("Sensor %s.* was never added on the KATCP server.",
                                name)
            return

        attr_dformat = self.inspecting_client.device_attributes[name].data_format
        if attr_dformat == AttrDataFormat.SPECTRUM:
            number_of_items = 0
            if isinstance(value, np.ndarray):
                number_of_items = value.size
            else:
                number_of_items = len(value)

            for index in xrange(number_of_items):
                try:
                    sensor = self.katcp_server.get_sensor(name + '.' + str(index))
                except ValueError as verr:
                    # AR 2016-05-19 TODO Need a robust way of dealing
                    # with not implemented sensors
                    self._logger.info('Sensor not implemented yet!' + str(verr))
                else:
                    status = TANGO_ATTRIBUTE_QUALITY_TO_KATCP_SENSOR_STATUS[quality]
                    sensor.set_value(value[index], status=status, timestamp=timestamp)
        else:
            try:
                sensor = self.katcp_server.get_sensor(name)
            except ValueError as verr:
                # AR 2016-05-19 TODO Need a robust way of dealing
                # with not implemented sensors
                self._logger.info('Sensor not implemented yet!' + str(verr))
            else:
                if sensor.type == 'discrete':
                    value = sensor.params[value]
                status = TANGO_ATTRIBUTE_QUALITY_TO_KATCP_SENSOR_STATUS[quality]
                sensor.set_value(value, status=status, timestamp=timestamp)

    @classmethod
    def from_addresses(cls, katcp_server_address, tango_device_address, logger=log):
        """Instantiate TangoDevice2KatcpProxy from network addresses

        Parameters
        ==========
        katcp_server_address : tuple (hostname : str, port : int)
            Address where the KATCP server interface should listen
        tango_device_address : str
            Tango address for the device to be translated

        """
        tango_device_proxy = cls.get_tango_device_proxy(tango_device_address)
        tango_inspecting_client = TangoInspectingClient(tango_device_proxy, logger=logger)
        katcp_host, katcp_port = katcp_server_address
        katcp_server = TangoProxyDeviceServer(katcp_host, katcp_port)
        katcp_server.set_concurrency_options(thread_safe=False, handler_thread=False)
        return cls(katcp_server, tango_inspecting_client, logger=logger)

    @staticmethod
    def get_tango_device_proxy(device_name, retry_time=2):
        tango_dp = None
        while not tango_dp:
            try:
                tango_dp = tango.DeviceProxy(device_name)
            except tango.DevFailed as dferr:
                dferr_reasons = set([arg.reason for arg in dferr.args])
                dferr_desc = set([arg.desc for arg in dferr.args])
                for reason, description in zip(dferr_reasons, dferr_desc):
                    log.error("{} : {}".format(reason, description))
                time.sleep(retry_time)
        return tango_dp

    def wait_for_device(self, tango_device_proxy, retry_time=2):
        """Get the translator to wait until it has established a connection with the
           device server and/or for the device server to be up and running.
        """
        is_device_connected = False
        while not is_device_connected:
            try:
                tango_device_proxy.reconnect(True)
            except tango.DevFailed as conerr:
                conerr_reasons = set([arg.reason for arg in conerr.args])
                conerr_desc = set([arg.desc for arg in conerr.args])
                for reason, description in zip(conerr_reasons, conerr_desc):
                    self._logger.error("{} : {}".format(reason, description))
                time.sleep(retry_time)
            else:
                is_device_connected = True

def tango2katcp_main(args=None, start_ioloop=True):
    from argparse import ArgumentParser
    from mkat_tango.translators.utilities import address

    parser = ArgumentParser(
        description="Launch Tango device -> KATCP translator")
    parser.add_argument('-l', '--loglevel', default='INFO',
                        help='Level for logging as per Python loglevel names, '
                        '"NO" for no log config. Default: %(default)s')
    parser.add_argument("--katcp-server-address", type=address,
                        help="HOST:PORT for the device to listen on", required=True)
    parser.add_argument('tango_device_address', type=str, help=
                        'Address of the tango device to connect to '
                        '(in tango format)')

    opts = parser.parse_args(args=args)

    loglevel = opts.loglevel.upper()
    if loglevel != 'NO':
        python_loglevel = getattr(logging, loglevel)
        logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - '
        '%(pathname)s : %(lineno)d - %(message)s',
            level=python_loglevel)

    ioloop = tornado.ioloop.IOLoop.current()
    proxy = TangoDevice2KatcpProxy.from_addresses(
        opts.katcp_server_address, opts.tango_device_address)
    ioloop.add_callback(proxy.start)
    if start_ioloop:
        try:
            ioloop.start()
        except KeyboardInterrupt:
            proxy.stop()

if __name__ == '__main__':
    tango2katcp_main()
