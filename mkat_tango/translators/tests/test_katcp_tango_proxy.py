# test_katcp_tango_proxy.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

import future
import logging
import mock
import os
import shutil
import socket
import subprocess
import tempfile
import textwrap
import time
import unittest

from builtins import object, range

import pkg_resources

import tango.server
import tornado.testing
import tornado.gen

from tango import (
    Attr,
    AttrDataFormat,
    DevFailed,
    DeviceProxy,
    DevLong,
    DevVoid,
)
from tango.test_context import DeviceTestContext, MultiDeviceTestContext

from katcp import Message, Sensor
from katcp.compat import ensure_native_str
from katcp.testutils import (
    BlockingTestClient,
    mock_req,
    start_thread_with_cleanup,
)
from mkat_tango import testutils
from mkat_tango.translators import katcp_tango_proxy, utilities
from mkat_tango.translators.tests.test_tango_inspecting_client import (
    ClassCleanupUnittestMixin,
    TangoTestDevice,
)
from tango import (
    Attr,
    AttrDataFormat,
    DevFailed,
    DeviceProxy,
    DevLong,
    DevVoid,
)
from tango.server import command
from tango.test_context import DeviceTestContext, get_host_ip
from tango_simlib import tango_sim_generator
from tango_simlib.utilities import helper_module
from tango_simlib.utilities.testutils import cleanup_tempfile


LOGGER = logging.getLogger(__name__)

KATCP_REQUEST_DOC_TEMPLATE = textwrap.dedent(
    """
    ?{cmd_name} {dtype_in} -> {dtype_out}

    Input Parameter
    ---------------

    {doc_in}

    Returns
    -------

    {doc_out}
    """
).lstrip()


SPECTRUM_ATTR = {
    "SpectrumDevDouble": [
        "SpectrumDevDouble.0",
        "SpectrumDevDouble.1",
        "SpectrumDevDouble.2",
        "SpectrumDevDouble.3",
        "SpectrumDevDouble.4",
    ]
}


class TangoDevice2KatcpProxy_BaseMixin(ClassCleanupUnittestMixin):
    DUT = None

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix="tango", suffix=".db")
        # It turns out that we need to explicitly specify the port number to have the
        # events working properly.
        host = socket.getfqdn()
        # https://github.com/tango-controls/pytango/blob/develop/tests/test_event.py#L83
        cls.tango_context = DeviceTestContext(
            TangoTestDevice, db=cls.tango_db, port=helper_module.get_port(), host=host
        )
        start_thread_with_cleanup(cls, cls.tango_context)
        cls.tango_device_address = cls.tango_context.get_device_access()

    def setUp(self):
        super(TangoDevice2KatcpProxy_BaseMixin, self).setUp()
        self.DUT = katcp_tango_proxy.TangoDevice2KatcpProxy.from_addresses(
            ("", 0), self.tango_device_address, polling=True
        )
        if hasattr(self, "io_loop"):
            self.DUT.set_ioloop(self.io_loop)
            self.io_loop.add_callback(self.DUT.start)
            self.addCleanup(self.DUT.stop, timeout=None)
        else:
            start_thread_with_cleanup(self, self.DUT, start_timeout=1)
        self.katcp_server = self.DUT.katcp_server
        self.tango_device_proxy = self.DUT.inspecting_client.tango_dp
        self.tango_test_device = TangoTestDevice.instances[self.tango_device_proxy.name()]
        self.katcp_address = self.katcp_server.bind_address
        self.host, self.port = self.katcp_address


class test_TangoDevice2KatcpProxy(TangoDevice2KatcpProxy_BaseMixin, unittest.TestCase):
    def setUp(self):
        super(test_TangoDevice2KatcpProxy, self).setUp()
        self.client = BlockingTestClient(self, self.host, self.port)
        start_thread_with_cleanup(self, self.client, start_timeout=1)
        self.client.wait_protocol(timeout=1)

    def test_from_address(self):
        self.assertEqual(self.client.is_connected(), True)
        reply, informs = self.client.blocking_request(Message.request("watchdog"))
        self.assertTrue(reply.reply_ok(), True)

    def test_sensor_attribute_match(self):
        reply, informs = self.client.blocking_request(Message.request("sensor-list"))
        sensor_list = {ensure_native_str(inform.arguments[0]) for inform in informs}
        attribute_list = set(self.tango_device_proxy.get_attribute_list())

        attributes = {
            attr_name: self.tango_device_proxy.get_attribute_config(attr_name)
            for attr_name in self.tango_device_proxy.get_attribute_list()
        }

        # The SpectrumDevDouble attribute name needs to be broken down to the KATCP
        # equivalent.
        for attr_name, attr_config in list(attributes.items()):
            if attr_config.data_format == AttrDataFormat.SPECTRUM:
                attribute_list.remove(attr_name)
                for index in range(attr_config.max_dim_x):
                    attribute_list.add(attr_name + "." + str(index))

        NOT_IMPLEMENTED_SENSORS = {"ScalarDevEncoded"}
        attribute_list_ = attribute_list - NOT_IMPLEMENTED_SENSORS
        self.assertEqual(
            attribute_list_,
            sensor_list,
            "\n\n!KATCP server sensor list differs from the TangoTestServer "
            "attribute list!\n\nThese sensors are"
            " extra:\n%s\n\nFound these attributes with no corresponding sensors:\n%s"
            % (
                "\n".join(sorted(sensor_list - attribute_list_)),
                "\n".join(sorted(attribute_list_ - sensor_list)),
            ),
        )

    def test_initial_attribute_sensor_values(self):
        sensors = self.katcp_server.get_sensors()
        attributes = self.tango_test_device.attr_return_vals
        for sensor in sensors:
            sensor_value = sensor.value()
            if sensor.name in ["State", "Status"]:
                # This sensors are handled specially since they are tango library
                # Attributes with State returning a device state object
                if sensor.name in ["State"]:
                    state = str(self.tango_device_proxy.state())
                    # tango._tango.DevState.ON is device state object
                    self.assertEqual(sensor_value, state)
                else:
                    status = self.tango_device_proxy.status()
                    self.assertEqual(sensor_value, status)
            elif sensor.name in SPECTRUM_ATTR["SpectrumDevDouble"]:
                attribute_value = attributes["SpectrumDevDouble"][0]
                index = int(sensor.name.split(".")[1])
                self.assertEqual(sensor_value, attribute_value[index])
            else:
                attr_name = utilities.katcpname2tangoname(sensor.name)
                attribute_value = attributes[attr_name][0]
                if sensor.name in ["ScalarDevEnum"]:
                    self.assertEqual({"ONLINE", "OFFLINE", "RESERVE"}, set(sensor.params))
                    self.assertEqual(sensor_value, sensor.params[attribute_value])
                else:
                    self.assertEqual(sensor_value, attribute_value)

    def test_attribute_sensor_update(self):
        sensors = []
        observers = {}
        # when polling at a period of less than 50 ms, tango becomes
        # inconsistent with the updates generated  i.e. the observed
        # time difference between updates fluctuates (50+-20 ms)
        poll_period = 50
        num_periods = 10
        # sleep time is 10 poll periods plus a little
        sleep_time = poll_period / 1000.0 * (num_periods + 0.5)
        testutils.set_attributes_polling(
            self,
            self.tango_device_proxy,
            self.tango_test_device,
            {attr: poll_period for attr in self.tango_device_proxy.get_attribute_list()},
        )

        # Information about EXCLUDED_ATTRS
        # "State" - Tango library attribute, Cannot change event_period
        # "Status" - Tango library attribute, Cannot change event_period
        # "ScalarDevEncoded" - Not implemented sensor, to be removed once
        # attribute type DevEncoded is handled as katcp server sensor types
        EXCLUDED_ATTRS = {"State", "Status", "ScalarDevEncoded"}

        for attr_name in self.tango_device_proxy.get_attribute_list():
            if attr_name not in EXCLUDED_ATTRS:
                # Instantiating observers and attaching them onto the katcp
                # sensors to allow logging of periodic event updates into a list

                # The default sampling strategy is 'change' and therefore subscription to
                # these attributes is successful and it doesn't fallback to subscribing
                # to periodic events. So no updates are expected from them.
                if attr_name in (
                    "ScalarDevEnum",
                    "ScalarBool",
                    "ScalarDevString",
                    "ScalarDevDoubleEvents",
                ):
                    continue
                if attr_name == "SpectrumDevDouble":
                    for attr_name_ in SPECTRUM_ATTR["SpectrumDevDouble"]:
                        observers[attr_name_] = observer = SensorObserver()
                        attr_name_ = utilities.tangoname2katcpname(attr_name_)
                        self.katcp_server.get_sensor(attr_name_).attach(observer)
                        sensors.append(attr_name_)
                else:
                    observers[attr_name] = observer = SensorObserver()
                    attr_name = utilities.tangoname2katcpname(attr_name)
                    self.katcp_server.get_sensor(attr_name).attach(observer)
                    sensors.append(attr_name)
            else:
                LOGGER.debug("Found unexpected attributes")
        time.sleep(sleep_time)

        for sensor in sensors:
            # TODO (KM 24-05-2018) This attributes have no set event properties. Need to
            # set these properties in the device's attribute definitions. However this
            # test is not for that. I will need to test each event individually for this
            # attributes: ScalarDevLong, ScalarDevUChar, ScalarDevDouble.
            self.katcp_server.get_sensor(sensor).detach(observer)
            obs = observers[sensor]
            number_of_updates = len(obs.updates)
            self.assertAlmostEqual(
                number_of_updates,
                num_periods,
                msg="Not enough updates for sensor: {}".format(sensor),
                delta=2,
            )

    def test_attribute_sensor_value_update(self):
        # instantiate a sensor observer to monitor sensor value updates
        observer = SensorObserver()
        sensor = utilities.tangoname2katcpname("ScalarDevEnum")
        self.katcp_server.get_sensor(sensor).attach(observer)

        # flip between two values 5x and for each
        # operation wait a while for updates to happen
        idx = 0
        num_periods = 5
        for _ in range(num_periods):
            idx += 1
            self.tango_device_proxy.ScalarDevEnum = idx
            time.sleep(1)
            if idx == 2:
                idx = 0

        self.katcp_server.get_sensor(sensor).detach(observer)
        number_of_updates = len(observer.updates)
        self.assertAlmostEqual(
            number_of_updates,
            num_periods,
            msg="Not enough updates for sensor: {}".format(sensor),
            delta=2,
        )

    def test_requests_list(self):
        tango_td = self.tango_test_device
        self.client.test_help(
            (
                ("Init", "?Init DevVoid -> DevVoid"),
                ("Status", "?Status DevVoid -> DevString"),
                # TODO NM 2016-05-20 Need to check what State should actually be
                #  and implement
                ("State", "?State DevVoid -> DevState"),
                (
                    "ReverseString",
                    KATCP_REQUEST_DOC_TEMPLATE.format(
                        cmd_name="ReverseString", **tango_td.ReverseString_command_kwargs
                    ),
                ),
                (
                    "MultiplyInts",
                    KATCP_REQUEST_DOC_TEMPLATE.format(
                        cmd_name="MultiplyInts", **tango_td.MultiplyInts_command_kwargs
                    ),
                ),
                (
                    "Void",
                    KATCP_REQUEST_DOC_TEMPLATE.format(
                        cmd_name="Void",
                        dtype_in="DevVoid",
                        doc_in="Void",
                        dtype_out="DevVoid",
                        doc_out="Void",
                    ),
                ),
                (
                    "MultiplyDoubleBy3",
                    KATCP_REQUEST_DOC_TEMPLATE.format(
                        cmd_name="MultiplyDoubleBy3",
                        **tango_td.MultiplyDoubleBy3_command_kwargs
                    ),
                ),
            )
        )

    def test_request(self):
        mid = 5
        reply, _ = self.client.blocking_request(
            Message.request("ReverseString", "polony", mid=mid)
        )
        self.assertEqual(str(reply), "!ReverseString[{}] ok ynolop".format(mid))

    def test_command_request_add_remove(self):
        def cmd_printString(self):
            """A new command."""
            return "DONE!"

        # Check that the request/command did not exist before
        self.assertNotIn("cmd_printString", self.katcp_server.get_request_list())
        self.assertNotIn("cmd_printString", self.tango_device_proxy.get_command_list())

        cmd = tango.server.command(
            f=cmd_printString,
            dtype_in=DevVoid,
            doc_in="",
            dtype_out=str,
            doc_out="",
            green_mode=None,
        )
        self.tango_test_device.cmd_printString = cmd_printString
        self.tango_test_device.add_command(cmd, device_level=True)
        time.sleep(0.5)  # Find alternative, rather than sleeping

        # Check that the request/command exists.
        self.assertIn("cmd_printString", self.tango_device_proxy.get_command_list())
        self.assertIn("cmd_printString", self.katcp_server.get_request_list())

        # Now remove the command.
        self.tango_test_device.remove_command("cmd_printString")
        delattr(self.tango_test_device, "cmd_printString")
        time.sleep(0.5)

        # Check that the request/command has been removed.
        self.assertNotIn("cmd_printString", self.tango_device_proxy.get_command_list())
        self.assertNotIn("cmd_printString", self.katcp_server.get_request_list())

    def test_attribute_sensor_add_remove(self):
        def read_attributes(self, attr):
            return 1

        # Check that the attribute/sensor did not exist before.
        self.assertNotIn("test-attr", self.katcp_server.get_sensor_list())
        self.assertNotIn("test_attr", self.tango_device_proxy.get_attribute_list())

        attr = Attr("test_attr", DevLong)
        self.tango_test_device.add_attribute(attr, read_attributes)
        time.sleep(0.5)  # Find alternative, rather than sleeping
        self.assertIn("test_attr", self.tango_device_proxy.get_attribute_list())
        self.assertIn("test-attr", self.katcp_server.get_sensor_list())

        # Now remove the attribute.
        self.tango_test_device.remove_attribute("test_attr")
        time.sleep(0.5)

        # Check that the attribute/sensor has been removed.
        self.assertNotIn("test_attr", self.tango_device_proxy.get_attribute_list())
        self.assertNotIn("test-attr", self.katcp_server.get_sensor_list())

    def test_setup_attribute_sampling(self):
        def read_attributes(self, attr):
            return 1

        with mock.patch.object(
            self.DUT.inspecting_client, "setup_attribute_sampling"
        ) as sec:
            attr = Attr("test_attr", DevLong)
            self.tango_test_device.add_attribute(attr, read_attributes)
            time.sleep(0.5)  # Find alternative, rather than sleeping

            # Check that test_attr was added to attribute map dictionary
            self.assertIn("test_attr", self.DUT.inspecting_client.orig_attr_names_map)

            # Check that attribute sampling was recalled for the new attribute
            sec.assert_called_with(
                ["ScalarDevEncoded", "test_attr"], server_polling_fallback=True
            )

            # Remove the attribute.
            self.tango_test_device.remove_attribute("test_attr")
            time.sleep(0.5)


class test_TangoDevice2KatcpProxyAsync(
    TangoDevice2KatcpProxy_BaseMixin, tornado.testing.AsyncTestCase
):
    @tornado.gen.coroutine
    def _test_cmd_handler(self, cmd_name, request_args, expected_reply_args):
        device_proxy = self.tango_context.device
        device_proxy_spy = mock.Mock(wraps=device_proxy)
        cmd_info = device_proxy.command_query(cmd_name)
        handler = katcp_tango_proxy.tango_cmd_descr2katcp_request(
            cmd_info, device_proxy_spy
        )

        ## Check that the docstring is correct
        # Do dict(...) to make a copy so that we don't mess with the original
        command_kwargs = dict(
            getattr(self.tango_test_device, cmd_name + "_command_kwargs")
        )
        if "dtype_in" not in command_kwargs:
            command_kwargs["dtype_in"] = "DevVoid"
            command_kwargs["doc_in"] = "Void"
        if "dtype_out" not in command_kwargs:
            command_kwargs["dtype_out"] = "DevVoid"
            command_kwargs["doc_out"] = "Void"

        expected_docstring = KATCP_REQUEST_DOC_TEMPLATE.format(
            cmd_name=cmd_name, **command_kwargs
        )
        self.assertEqual(handler.__doc__, expected_docstring)

        ## To a test request
        mock_katcp_server = mock.Mock(spec_set=self.DUT.katcp_server)
        req = mock_req(cmd_name, *request_args, server=mock_katcp_server)
        result = yield handler(mock_katcp_server, req, req.msg)
        # check if expected reply is recieved
        expected_msg = Message.reply(cmd_name, *expected_reply_args)
        self.assertEqual(str(result), str(expected_msg))
        # check that tango device proxy is called once and only once.
        self.assertEqual(device_proxy_spy.command_inout.call_count, 1)

    @tornado.testing.gen_test
    def test_cmd2request_ReverseString(self):
        """Test request handler for the TangoTestServer ReverseString command

        """
        yield self._test_cmd_handler(
            cmd_name="ReverseString",
            request_args=["abcdef"],
            expected_reply_args=["ok", "fedcba"],
        )

    @tornado.testing.gen_test
    def test_cmd2request_MultiplyInts(self):
        """Test request handler for the TangoTestServer MultiplyInts command

        """
        yield self._test_cmd_handler(
            cmd_name="MultiplyInts",
            request_args=[1, 3, 7, 9],
            expected_reply_args=["ok", 1 * 3 * 7 * 9],
        )

    @tornado.testing.gen_test
    def test_cmd2request_MultiplyInt(self):
        """Test request handler for the TangoTestServer MultiplyInts command
        with a single item

        """
        yield self._test_cmd_handler(
            cmd_name="MultiplyInts", request_args=[88], expected_reply_args=["ok", 88]
        )

    @tornado.testing.gen_test
    def test_cmd2request_MultiplyDoubleBy3(self):
        """Test request handler for the TangoTestServer MultiplyDoubleBy2MultiplyInts command

        """
        yield self._test_cmd_handler(
            cmd_name="MultiplyDoubleBy3",
            request_args=[0.5],
            expected_reply_args=["ok", 0.5 * 3.0],
        )

    @tornado.testing.gen_test
    def test_cmd2request_Void(self):
        """Test request handler for the TangoTestServer ReverseString command

        """
        yield self._test_cmd_handler(
            cmd_name="Void", request_args=[], expected_reply_args=["ok"]
        )

    @tornado.testing.gen_test
    def test_cmd2request_State(self):
        """Test request handler for the TangoTestServer State command

        """
        yield self._test_cmd_handler(
            cmd_name="State", request_args=[], expected_reply_args=["ok", "ON"]
        )


class SensorObserver(object):
    def __init__(self):
        self.updates = []

    def update(self, sensor, reading):
        self.updates.append((sensor, reading))
        LOGGER.debug("Received {!r} for attr {!r}".format(sensor, reading))


class test_TangoDeviceShutdown(ClassCleanupUnittestMixin, unittest.TestCase):
    """This tests that the sensor statuses change to failure when the we loose
       connection to the TANGO device.
    """

    longMessage = True

    @classmethod
    def setUpClass(cls):
        cls.tango_port = helper_module.get_port()
        cls.tango_host = socket.getfqdn()
        cls.data_descr_files = []
        cls.data_descr_files.append(
            pkg_resources.resource_filename(
                "tango_simlib.tests.config_files", "Weather.xmi"
            )
        )
        cls.temp_dir = cleanup_tempdir()
        cls.sim_device_class = tango_sim_generator.get_device_class(cls.data_descr_files)
        cls.device_name = "test/nodb/tangodeviceserver"
        server_name = "weather_ds"
        server_instance = "test"
        database_filename = os.path.join("{}", "{}_tango.db").format(
            cls.temp_dir, server_name
        )
        sim_device_prop = dict(sim_data_description_file=cls.data_descr_files[0])
        sim_test_device_prop = dict(model_key=cls.device_name)
        tango_sim_generator.generate_device_server(
            server_name, cls.data_descr_files, cls.temp_dir
        )
        helper_module.append_device_to_db_file(
            server_name,
            server_instance,
            cls.device_name,
            database_filename,
            cls.sim_device_class,
            sim_device_prop,
        )
        helper_module.append_device_to_db_file(
            server_name,
            server_instance,
            "%scontrol" % cls.device_name,
            database_filename,
            "%sSimControl" % cls.sim_device_class,
            sim_test_device_prop,
        )
        cls.sub_proc = subprocess.Popen(
            [
                "python{}".format("" if future.utils.PY2 else "3"),
                "{}/{}".format(cls.temp_dir, server_name),
                server_instance,
                "-file={}".format(database_filename),
                "-ORBendPoint",
                "giop:tcp::{}".format(cls.tango_port),
            ]
        )

        # Note that tango demands that connection to the server must
        # be delayed by atleast 1000 ms of device server start up.
        time.sleep(1)
        cls.sim_device = DeviceProxy(
            "%s:%s/test/nodb/tangodeviceserver#dbase=no"
            % (cls.tango_host, cls.tango_port)
        )

    def setUp(self):
        super(test_TangoDeviceShutdown, self).setUp()
        self.tango_device_address = "tango://%s:%s/%s#dbase=no" % (
            self.tango_host,
            self.tango_port,
            self.device_name,
        )
        self.DUT = katcp_tango_proxy.TangoDevice2KatcpProxy.from_addresses(
            ("", 0), self.tango_device_address, polling=True
        )
        if hasattr(self, "io_loop"):
            self.DUT.set_ioloop(self.io_loop)
            self.io_loop.add_callback(self.DUT.start)
            self.addCleanup(self.DUT.stop, timeout=None)
        else:
            start_thread_with_cleanup(self, self.DUT, start_timeout=1)
        self.katcp_server = self.DUT.katcp_server
        self.tango_device_proxy = self.DUT.inspecting_client.tango_dp
        self.katcp_address = self.katcp_server.bind_address
        self.katcp_host, self.katcp_port = self.katcp_address

        self.client = BlockingTestClient(self, self.katcp_host, self.katcp_port)
        start_thread_with_cleanup(self, self.client, start_timeout=1)
        self.client.wait_protocol(timeout=1)

    def test_device_shutdown(self):
        """Test sensor status updates when TANGO device goes offline."""
        self.assertGreater(self.sim_device.ping(), 0, "TANGO device is offline")

        sensors = self.katcp_server.get_sensors()
        for sensor in sensors:
            self.assertEqual(
                sensor.status(), Sensor.NOMINAL, "Sensor %s status nominal." % sensor.name
            )

        self.sub_proc.kill()
        with self.assertRaises(DevFailed):
            self.sim_device.ping()

        time.sleep(12)  # Need to sleep to allow sensors to update.
        for sensor in sensors:
            self.assertEqual(
                sensor.status(),
                Sensor.FAILURE,
                "Sensor %s status in failure." % sensor.name,
            )


class SimpleDevice1(tango.server.Device):
    @tango.server.attribute(dtype=int, doc="temperature \xb0C", unit="\xb0C")
    def attr1(self):
        return 123

    @tango.server.command(
        dtype_in=str,
        dtype_out=str,
        doc_in="temperature in \xb0C",
        doc_out="temperature out \xb0C",
    )
    def cmd1(self, argin):
        return "{}:reply1".format(argin)


class SimpleDevice2(tango.server.Device):
    @tango.server.attribute(dtype=int)
    def attr2(self):
        return 456

    @tango.server.command(dtype_in=str, dtype_out=str)
    def cmd2a(self, argin):
        return "{}:reply2a".format(argin)

    @tango.server.command(dtype_in=str, dtype_out=str)
    def cmd2b(self, argin):
        return "{}:reply2b".format(argin)


class test_TangoDevice2KatcpProxyMultipleDevices(
    ClassCleanupUnittestMixin, unittest.TestCase
):
    @classmethod
    def setUpClassWithCleanup(cls):
        cls.devices_info = (
            {"class": SimpleDevice1, "devices": [{"name": "test/simple/1"}]},
            {"class": SimpleDevice2, "devices": [{"name": "test/simple/2"}]},
        )
        cls.tango_context = MultiDeviceTestContext(cls.devices_info)
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(test_TangoDevice2KatcpProxyMultipleDevices, self).setUp()
        self.translators = {}
        self.clients = {}
        for device_info in self.devices_info:
            device_class = device_info["class"]
            device_name = device_info["devices"][0]["name"]

            # start translator
            translator = katcp_tango_proxy.TangoDevice2KatcpProxy.from_addresses(
                ("", 0), self.tango_context.get_device_access(device_name), polling=True
            )
            start_thread_with_cleanup(self, translator, start_timeout=1)
            self.translators[device_class] = translator

            # start KATCP client to the translator
            host, port = translator.katcp_server.bind_address
            client = BlockingTestClient(self, host, port)
            start_thread_with_cleanup(self, client, start_timeout=1)
            client.wait_protocol(timeout=1)
            self.clients[device_class] = client

    def test_requests_for_multiple_devices(self):
        device_requests = {
            SimpleDevice1: {"cmd1": b"test:reply1"},
            SimpleDevice2: {"cmd2a": b"test:reply2a", "cmd2b": b"test:reply2b"},
        }
        for device_class, requests in device_requests.items():
            client = self.clients[device_class]
            for request, expected_value in requests.items():
                reply, _ = client.blocking_request(Message.request(request, "test"))
                self.assertEqual(reply.arguments[1], expected_value)

    def test_sensor_readings_for_multiple_devices(self):
        device_sensors = {
            SimpleDevice1: {"attr1": 123},
            SimpleDevice2: {"attr2": 456},
        }
        for device_class, sensors in device_sensors.items():
            client = self.clients[device_class]
            for sensor, expected_value in sensors.items():
                actual_value = client.get_sensor_value(sensor, int)
                self.assertEqual(actual_value, expected_value)

    def test_latin1_encoded_as_utf8_in_sensors(self):
        server = self.translators[SimpleDevice1].katcp_server
        sensor = server.get_sensor("attr1")
        expected_description = u"temperature °C"
        expected_units = u"°C"
        if future.utils.PY2:
            expected_description = expected_description.encode(encoding="utf-8")
            expected_units = expected_units.encode(encoding="utf-8")
        self.assertEqual(sensor.description, expected_description)
        self.assertEqual(sensor.units, expected_units)

    def test_latin1_encoded_as_utf8_in_requests(self):
        server = self.translators[SimpleDevice1].katcp_server
        request = server._request_handlers["cmd1"]
        expected_doc_in = u"temperature in °C"
        expected_doc_out = u"temperature out °C"
        if future.utils.PY2:
            expected_doc_in = expected_doc_in.encode(encoding="utf-8")
            expected_doc_out = expected_doc_out.encode(encoding="utf-8")
        self.assertIn(expected_doc_in, request.__doc__)
        self.assertIn(expected_doc_out, request.__doc__)


def cleanup_tempdir(*mkdtemp_args, **mkdtemp_kwargs):
    """Return filname of a new tempfile.

    Will not raise an error if the directory is not present when trying to delete.

    Extra args and kwargs are passed on to the tempfile.mkdtemp call

    """
    dirname = tempfile.mkdtemp(*mkdtemp_args, **mkdtemp_kwargs)

    def cleanup():
        try:
            shutil.rmtree(dirname)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

    return dirname
