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
import time
import unittest
import mock

import tornado.testing
import tornado.gen
import tango

from tango.server import DeviceMeta
from tango.test_context import DeviceTestContext

from katcp import DeviceServer, Sensor, ProtocolFlags, Message
from katcp.resource_client import IOLoopThreadWrapper
from katcp.testutils import start_thread_with_cleanup, BlockingTestClient
from katcp.kattypes import Float, Timestamp, request, return_reply
from katcore.testutils import cleanup_tempfile

from mkat_tango.translators.tango_katcp_proxy import (get_tango_device_server,
                                                      remove_tango_server_attribute_list,
                                                      add_tango_server_attribute_list,
                                                      create_command2request_handler,
                                                      TangoDeviceServerBase,
                                                      get_katcp_request_data)
from mkat_tango.translators.katcp_tango_proxy import is_tango_device_running
from mkat_tango.translators.utilities import katcpname2tangoname, tangoname2katcpname
from mkat_tango.translators.tests.test_tango_inspecting_client import (
        ClassCleanupUnittestMixin)


logger = logging.getLogger(__name__)

sensors = {
        'failure-present': Sensor.boolean(
            "failure-present",
            "Indicates whether at least one failure that prevents antenna "
            "movement is currently latched", ""),
        'reboot-reason': Sensor.discrete(
            "reboot-reason",
            "Reports reason for last reboot of the ACU",
            "", ['powerfailure', 'plc-watchdog', 'remote', 'other']),
        'actual-azim': Sensor.float(
            "actual-azim", "Actual azimuth position",
            "deg", [-183.32, 275.0], 32.9),
        'invalid-float': Sensor.float(
            "invalid-float", "Float with bad min/max", "", [0, 0]),
        'a-bad-bad-int': Sensor.integer(
            "a-bad-bad-int", "Int with bad min/max", "", [10, 10]),
        'track-stack-size': Sensor.integer(
            "track-stack-size",
            "The number of track samples available in the ACU sample stack",
            "", [0, 3000]),
        'add-result': Sensor.float(
            "add-result", "Last ?add result.", "", [-10000, 10000]),
        'time-result': Sensor.timestamp(
            "time-result", "Last ?time result.", "", [0.00, 1000000000.00]),
        'gps-nmea': Sensor.string(
            "gps-nmea", "GPS NMEA string details received", ""),
        'ntp-timestamp': Sensor.timestamp(
            "ntp-timestamp",
            "NTP server timestamp", "", [0.00, 1000000000.00]),
        'ntp-lru': Sensor.address("ntp-lru", "NTP server IP address", "")}

# Names of the KATCP sensors that cannot be converted to a valid tango attribute
invalid_sensor_names = set(['invalid-float', 'a-bad-bad-int'])

default_attributes = {
    'State', 'Status', 'NumErrorTranslatingSensors',
    'ErrorTranslatingSensors', 'Replies', 'Informs'}

default_commands = {'Init', 'Status', 'State'}

server_host = ""
server_port = 0


class KatcpTestDevice(DeviceServer):

    VERSION_INFO = ("example-api", 1, 0)
    BUILD_INFO = ("example-implementation", 0, 1, "")

    def setup_sensors(self):
        """Setup some server sensors."""
        for sensor in sensors.values():
            self.add_sensor(sensor)

    @request(Float(), Float())
    @return_reply(Float())
    def request_add(self, req, x, y):
        """Add two numbers

        Input Parameters
        ----------------
        x : kattypes.Float
        y : kattypes.Float

        """
        result = x + y
        self.get_sensor('add-result').set_value(result)
        return ("ok", result)

    @request()
    @return_reply(Timestamp())
    def request_time(self, req):
        """Return the current time in ms since the Unix Epoch."""
        result = time.time()
        self.get_sensor('time-result').set_value(result)
        return ("ok", result)


class KatcpTestDeviceValidSensorsOnly(DeviceServer):

    VERSION_INFO = ("example-api", 1, 0)
    BUILD_INFO = ("example-implementation", 0, 1, "")

    def setup_sensors(self):
        """Setup some server sensors."""
        for sensor in sensors.values():
            # Skip invalid sensors
            if sensor.name in invalid_sensor_names:
                continue
            self.add_sensor(sensor)


class TangoDeviceServer(TangoDeviceServerBase):
    __metaclass__ = DeviceMeta


class _test_KatcpTango2DeviceProxy(unittest.TestCase):
    longMessage = True
    device = TangoDeviceServer
    KatcpTestDeviceClass = KatcpTestDevice

    @classmethod
    def setUpClass(cls):
        cls.katcp_server = cls.KatcpTestDeviceClass(server_host, server_port)
        cls.katcp_server.start()
        address = cls.katcp_server.bind_address
        katcp_server_host, katcp_server_port = address
        cls.properties = dict(katcp_address=katcp_server_host + ':' +
                              str(katcp_server_port))
        cls.tango_context = DeviceTestContext(cls.device, properties=cls.properties)
        cls.tango_context.start()
        super(_test_KatcpTango2DeviceProxy, cls).setUpClass()

    def setUp(self):
        super(_test_KatcpTango2DeviceProxy, self).setUp()
        self.tango_dp = self.tango_context.device
        self.instance = TangoDeviceServer.instances[self.tango_dp.name()]
        self.ioloop = self.instance.tango_katcp_proxy.ioloop
        self.katcp_ic = self.instance.tango_katcp_proxy.katcp_inspecting_client
        self.katcp_ic.katcp_client.wait_protocol(timeout=2)
        self.ioloop_wrapper = IOLoopThreadWrapper(self.ioloop)
        self.in_ioloop = self.ioloop_wrapper.decorate_callable
        # Using these two lines for state consistency for tango ds, will be replaced.
        self.in_ioloop(self.katcp_ic.until_data_synced)()
        # TODO (KM 2016-06-23): Need to make use of the Tango device interface change
        # event instead of sleeping to allow the tango device server be configured.
        time.sleep(0.5)

        def cleanup_refs():
            del self.instance
        self.addCleanup(cleanup_refs)
        self.addCleanup(self._reset_katcp_server)
        # Need to reset the device server to its default configuration
        self.addCleanup(remove_tango_server_attribute_list,
                        self.instance, self.katcp_server._sensors)

    def _reset_katcp_server(self):
        """For removing any sensors that were added during testing
        """
        for sens_name in self.katcp_server._sensors.keys():
            if sens_name not in sensors.keys():
                self.katcp_server.remove_sensor(sens_name)

    @classmethod
    def tearDownClass(cls):
        cls.tango_context.stop()
        cls.katcp_server.stop()
        super(_test_KatcpTango2DeviceProxy, cls).tearDownClass()


class _test_KatcpTango2DeviceProxyCommands(ClassCleanupUnittestMixin,
                                           unittest.TestCase):
    longMessage = True

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.katcp_server = KatcpTestDevice(server_host, server_port)
        start_thread_with_cleanup(cls, cls.katcp_server)
        address = cls.katcp_server.bind_address
        katcp_server_host, katcp_server_port = address
        cls.properties = dict(katcp_address=katcp_server_host + ':' +
                              str(katcp_server_port))
        with mock.patch('mkat_tango.translators.tango_katcp_proxy.get_katcp_address'
                        ) as mock_get_katcp_address:
            mock_get_katcp_address.return_value = '{}:{}'.format(
                    katcp_server_host, katcp_server_port)
            cls.TangoDeviceServer = get_tango_device_server()
            cls.tango_context = DeviceTestContext(cls.TangoDeviceServer,
                                                 db=cls.tango_db,
                                                 properties=cls.properties)
        start_thread_with_cleanup(cls, cls.tango_context)

    def setUp(self):
        super(_test_KatcpTango2DeviceProxyCommands, self).setUp()
        self.device = self.tango_context.device
        self.instance = self.TangoDeviceServer.instances[self.device.name()]
        self.ioloop = self.instance.tango_katcp_proxy.ioloop
        self.katcp_ic = self.instance.tango_katcp_proxy.katcp_inspecting_client
        self.katcp_ic.katcp_client.wait_protocol(timeout=5.0)
        self.ioloop_wrapper = IOLoopThreadWrapper(self.ioloop)
        self.in_ioloop = self.ioloop_wrapper.decorate_callable
        # Using these two lines for state consistency for tango ds, will be replaced.
        self.in_ioloop(self.katcp_ic.until_data_synced)()
        # TODO (KM 2016-06-23): Need to make use of the Tango device interface change
           # event instead of sleeping to allow the tango device server be configured.
        time.sleep(0.5)

        def cleanup_refs():
            del self.instance
        self.addCleanup(cleanup_refs)
        self.addCleanup(self._reset_katcp_server)

    def _reset_katcp_server(self):
        """For removing any sensors that were added during testing
        """
        for sens_name in self.katcp_server._sensors.keys():
            if sens_name not in sensors.keys():
                self.katcp_server.remove_sensor(sens_name)

class test_KatcpTango2DeviceProxy(_test_KatcpTango2DeviceProxy):
    def test_connections(self):
        """Testing if both the TANGO client proxy and the KATCP inspecting clients
        have established a connection with their device servers, respectively.
        """
        is_proxy_connecting_to_server = is_tango_device_running(self.tango_dp)
        self.assertEqual(is_proxy_connecting_to_server, True,
                        "No connection established between client and server")
        self.assertEqual(self.katcp_ic.is_connected(), True,
                        "The KATCP inspecting client is not connected to the device"
                        " server")

    def test_update_tango_server_attribute_list(self):
        """Testing that the update methods (add/remove_tango_server_attribute_list
        method) works correctly.
        """
        # Reset the device server to its default configuration as the server is
        # reconfigured once the inspecting client gets state updates
        remove_tango_server_attribute_list(self.instance, sensors)
        # Get the default attributes of the device server
        device_attrs = set(list(self.tango_dp.get_attribute_list()))
        self.assertEquals(device_attrs, default_attributes,
                          "The device server has unexpected default attributes")
        add_tango_server_attribute_list(self.instance, sensors)

        device_attrs = set(list(self.tango_dp.get_attribute_list()))
        self.assertNotEquals(device_attrs, default_attributes,
                             "Attribute list was never updated")
        # Test if the number of attributes has increased after the update
        self.assertGreater(len(device_attrs), len(default_attributes),
                           "Attribute list was never updated")
        # Test if its possible to remove attributes from the device server.
        remove_tango_server_attribute_list(self.instance, sensors)
        device_attrs = set(list(self.tango_dp.get_attribute_list()))
        self.assertEquals(device_attrs, default_attributes,
                          "The device server has unexpected default attributes")

    def test_sensor_translation_errors(self):
        """Sensors untranslatable due to errors are properly reported?"""
        # Initial sensor list will include some invalid sensors
        # Check that the correct number and alarm quality are reported:
        reading = self.tango_dp.read_attribute('NumErrorTranslatingSensors')
        self.assertEqual(reading.value, len(invalid_sensor_names))
        self.assertEqual(reading.quality, tango.AttrQuality.ATTR_ALARM)
        # And the correct sensor names
        self.assertEqual(sorted(self.tango_dp.ErrorTranslatingSensors),
                         sorted(invalid_sensor_names))

    def test_expected_sensor_attributes(self):
        """Testing if the expected attribute list matches with the actual attribute list
           after adding the new attributes.
        """
        attr_list = list(self.tango_dp.get_attribute_list())
        for def_attr in default_attributes:
            attr_list.remove(def_attr)

        sens_names = sensors.keys()
        sensname2tangoname_list = []
        for sen_name in sens_names:
            if sen_name in invalid_sensor_names:
                continue
            sensname2tangoname_list.append(katcpname2tangoname(sen_name))
        self.assertEqual(set(attr_list), set(sensname2tangoname_list), "The attribute"
                         " list and the the sensor list do not match")

    def test_attribute_sensor_properties_match_direct_trans(self):
        """ Testing if the sensor object properties were translated correctly directly
        using the add method.
        """
        remove_tango_server_attribute_list(self.instance, sensors)
        add_tango_server_attribute_list(self.instance, sensors)
        for sensor in self.katcp_server._sensors.values():
            if sensor.name in invalid_sensor_names:
                continue
            attr_desc = self.tango_dp.get_attribute_config(
                                                       katcpname2tangoname(sensor.name))
            self.assertEqual(tangoname2katcpname(attr_desc.name), sensor.name,
                             "The sensor and the attribute name are not the same")
            self.assertEqual(attr_desc.description, sensor.description,
                             "The sensor and the attribute description are not"
                             " identical")
            self.assertEqual(attr_desc.unit, sensor.units,
                             "The sensor and the attribute unit are not identical")
            if sensor.stype in ['integer']:
                self.assertEqual(int(attr_desc.min_value), sensor.params[0],
                                 "The sensor and attribute min values are not"
                                 " identical")
                self.assertEqual(int(attr_desc.max_value), sensor.params[1],
                                 "The sensor and attribute max values are not"
                                 " identical")
            elif sensor.stype in ['float']:
                self.assertEqual(float(attr_desc.min_value), sensor.params[0],
                                 "The sensor and attribute min values are not"
                                 " identical")
                self.assertEqual(float(attr_desc.max_value), sensor.params[1],
                                 "The sensor and attribute max values are not"
                                 " identical")
            # TODO (KM) 14-06-2016: Need to check the params for the discrete sensor
                 #type once solution for DevEnum is found.
            elif sensor.stype == 'string':
                self.assertEqual(attr_desc.min_value, "Not specified",
                                 "The string sensor type object has unexpected"
                                 " min_value")
                self.assertEqual(attr_desc.max_value, "Not specified",
                                 "The string sensor type object has unexpected"
                                 " min_value")
                self.assertEqual(sensor.params, [],
                                 "The sensor object has a non-empty params list")

    def test_attribute_sensor_properties_match_via_proxy_trans(self):
        """ Testing if the sensor object properties were translated correctly using the
        proxy translator.
        """
        for sensor in self.katcp_server._sensors.values():
            if sensor.name in invalid_sensor_names:
                continue
            attr_desc = self.tango_dp.get_attribute_config(
                katcpname2tangoname(sensor.name))
            self.assertEqual(tangoname2katcpname(attr_desc.name), sensor.name,
                             "The sensor and the attribute name are not the same")
            self.assertEqual(attr_desc.description, sensor.description,
                             "The sensor and the attribute description are not"
                             " identical")
            self.assertEqual(attr_desc.unit, sensor.units,
                             "The sensor and the attribute unit are not identical")
            if sensor.stype in ['integer']:
                self.assertEqual(int(attr_desc.min_value), sensor.params[0],
                                 "The sensor and attribute min values are not"
                                 " identical")
                self.assertEqual(int(attr_desc.max_value), sensor.params[1],
                                 "The sensor and attribute max values are not"
                                 " identical")
            elif sensor.stype in ['float']:
                self.assertEqual(float(attr_desc.min_value), sensor.params[0],
                                 "The sensor and attribute min values are not"
                                 " identical")
                self.assertEqual(float(attr_desc.max_value), sensor.params[1],
                                 "The sensor and attribute max values are not"
                                 " identical")
            # TODO (KM) 14-06-2016: Need to check the params for the discrete sensor
            # type once solution for DevEnum is found.
            elif sensor.stype == 'string':
                self.assertEqual(attr_desc.min_value, "Not specified",
                                 "The string sensor type object has unexpected"
                                 " min_value")
                self.assertEqual(attr_desc.max_value, "Not specified",
                                 "The string sensor type object has unexpected"
                                 " min_value")
                self.assertEqual(sensor.params, [],
                                 "The sensor object has a non-empty params list")


    def test_sensor2attr_removal_updates(self):
        """Testing if removing a sensor from the KATCP device server also results in the "
        removal of the equivalent TANGO attribute on the TANGO device server.
        """
        initial_tango_dev_attr_list = set(list(self.tango_dp.get_attribute_list()))
        sensor_name = 'failure-present'
        self.assertIn(sensor_name, self.katcp_server._sensors.keys(), "Sensor not in"
                      " list")
        self.assertIn(katcpname2tangoname(sensor_name), initial_tango_dev_attr_list,
                      "The attribute was not removed")
        self.katcp_server.remove_sensor(sensor_name)
        self.katcp_server.mass_inform(Message.inform('interface-changed'))
        self.in_ioloop(self.katcp_ic.until_data_synced)()
        time.sleep(0.5)
        self.tango_dp.Status()
        current_tango_dev_attr_list = set(list(self.tango_dp.get_attribute_list()))
        self.assertNotIn(katcpname2tangoname(sensor_name), current_tango_dev_attr_list,
                      "The attribute was not removed")

    def test_sensor2attr_addition_updates(self):
        """Testing if adding a sensor to the KATCP device server also results in the "
        addition of the equivalent TANGO attribute on the TANGO device server.
        """
        initial_tango_dev_attr_list = set(list(self.tango_dp.get_attribute_list()))
        sens = Sensor(Sensor.FLOAT, "experimental-sens", "A test sensor", "",
                      [-1.5, 1.5])
        self.assertNotIn(sens.name, self.katcp_server._sensors.keys(), "Unexpected"
                      " sensor in the sensor list")
        self.assertNotIn(katcpname2tangoname(sens.name),
                         initial_tango_dev_attr_list,
                         "Unexpected attribute in the attribute list")
        self.katcp_server.add_sensor(sens)
        self.katcp_server.mass_inform(Message.inform('interface-changed'))
        self.in_ioloop(self.katcp_ic.until_data_synced)()
        time.sleep(0.5)
        current_tango_dev_attr_list = set(list(self.tango_dp.get_attribute_list()))
        self.assertIn(sens.name, self.katcp_server._sensors.keys(),
                      "Sensor was not added to the katcp device server.")
        self.assertIn(katcpname2tangoname(sens.name),
                      current_tango_dev_attr_list,
                      "Attribute was not added to the TANGO device server.")

    def _update_katcp_server_sensor_values(self, katcp_device_server):
        """Method that makes updates to all the katcp device server sensors.

        Parameters
        ----------
        katcp_device_server : KATCP DeviceServer
            The katcp device server for which sensor updates are applied to.

        Returns
        -------
        katcp_device_server : KATCP DeviveServer
            The same katcp server but with new sensor value updates.

        """
        for sensor in katcp_device_server.get_sensors():
            if sensor.stype in ['integer']:
                value = 5
                self.assertNotEqual(sensor.value(), value,
                        "Sensor {} value is identical to the value to be set".
                        format(sensor.name))
                sensor.set_value(value)
            elif sensor.stype in ['float']:
                value = 10.0
                self.assertNotEqual(sensor.value(), value,
                        "Sensor {} value is identical to the value to be set".
                        format(sensor.name))
                sensor.set_value(value)
            elif sensor.stype in ['boolean']:
                value = True
                self.assertNotEqual(sensor.value(), value,
                        "Sensor {} value is identical to the value to be set".
                        format(sensor.name))
                sensor.set_value(value)
            elif sensor.stype in ['discrete', 'string']:
                value = 'remote'  # used 'remote' for string values since is part of
                                 # descrete values in our katcp server descrete sensor.
                self.assertNotEqual(sensor.value(), value,
                        "Sensor {} value is identical to the value to be set".
                        format(sensor.name))
                sensor.set_value(value)
            elif sensor.stype in ['timestamp']:
                value = time.time()
                self.assertNotEqual(sensor.value(), value,
                        "Sensor {} value is identical to the value to be set".
                        format(sensor.name))
                sensor.set_value(value)
            elif sensor.stype in ['address']:
                value = ('localhost', 5000)
                self.assertNotEqual(sensor.value, value,
                        "Sensor {} value is identical to the value to be set".
                        format(sensor.name))
                sensor.set_value(value)
        return katcp_device_server

    def _wait_for_tango_attribute_to_update(
            self, attr_name, timeout=1, poll_period=0.025):
        """Keeps polling tango attribute from running device until the a value that
        is not None is found, otherwise timeout error exception is raised.

        Parameters
        ----------
        attr_name : str
            Name of tango attribute name to poll.
        timeout : int [defualt = 1 ]seconds
            Suspension time after which a RuntimeError is raise.
        poll_period : int [defualt = 0.025 ]seconds
            Period of sampling the value of the device attribute.

        """
        stoptime = time.time() + timeout
        value = getattr(self.tango_dp, attr_name)
        while value is None:
            value = getattr(self.tango_dp, attr_name, None)
            time.sleep(poll_period)
            if time.time() > stoptime:
                raise RuntimeError("TimeOutError : Tango device server not well"
                "configured. Attributes not updated")

    def test_sensor_attribute_value_update(self):
        """Testing if the KATCP server sensor updates reflect as attribute
        updates in the Tango device server
        """
        katcp_device_server = self._update_katcp_server_sensor_values(
                self.katcp_server)
        for sensor in katcp_device_server.get_sensors():
            if sensor.name in invalid_sensor_names:
                continue
            attribute_name = katcpname2tangoname(sensor.name)
            self._wait_for_tango_attribute_to_update(attribute_name)
            attribute_value = getattr(self.tango_dp, attribute_name)
            sensor_value = sensor.value()
            if type(sensor_value) is tuple:
                # Address sensor type contains a Tuple contaning (host, port) and
                # mapped to tango DevString type i.e "host:port"
                sensor_value = ':'.join(str(s) for s in sensor_value)
            self.assertEqual(attribute_value, sensor_value)

class test_KatcpTango2DeviceProxyValidSensorsOnly(_test_KatcpTango2DeviceProxy):
    KatcpTestDeviceClass = KatcpTestDeviceValidSensorsOnly

    def test_sensor_translation_errors(self):
        """No spurious sensor translation errors are reported?"""
        reading = self.tango_dp.read_attribute('NumErrorTranslatingSensors')
        self.assertEqual(reading.value, 0)
        self.assertEqual(reading.quality, tango.AttrQuality.ATTR_VALID)
        # And the no sensor names
        # TODO NM 2016-08-31 For some reason None is returned instead of an
        # empty list, tango bug?
        self.assertEqual(self.device.ErrorTranslatingSensors, None)


class test_KatcpTango2DeviceProxyCommands(_test_KatcpTango2DeviceProxyCommands):

    def test_inspection_of_requests(self):
        """Testing if the katcp blocking client succesfully obtained the katcp
        requests and whether translation was successful.
        """
        is_katcp_server_running = self.katcp_server.running()
        self.assertEqual(is_katcp_server_running, True,
                         "Katcp device server not running")
        katcp_server_host, katcp_server_port = self.katcp_server.bind_address
        with mock.patch('mkat_tango.translators.tango_katcp_proxy.get_katcp_address'
                        ) as mock_get_katcp_address:
            mock_get_katcp_address.return_value = '{}:{}'.format(
                    katcp_server_host, katcp_server_port)
            req_dict = get_katcp_request_data()
        command_list = [command.cmd_name for command in
                        self.device.command_list_query()]
        reqname2tangoname_list = []
        for req in req_dict.keys():
            katcp_tango_name = katcpname2tangoname(req)
            reqname2tangoname_list.append(katcp_tango_name)
            self.assertIn(katcp_tango_name, command_list)
        for def_command in default_commands:
            command_list.remove(def_command)
        self.assertEqual(set(command_list), set(reqname2tangoname_list),
                         "The command list and the request list do not match")

    def _test_command2request_handler(self, req_name, req_doc, with_parameters=False):
        """Testing the tango command handler with/without request parameters.

        Parameters
        ----------
        req_name : str
            KATCP request name
        req_doc : str
            KATCP request docstring
        with_parameters : bool
            Represent whether or not the request takes in parameters

        """
        command = create_command2request_handler(req_name, req_doc)
        # The format of the command attribute __tango_command__ is a tuple
        # (req_name, [[dtype_in, doc_in,], [dtype_out, doc_out], {}])
        doc_in = command.__tango_command__[1][0][1]
        doc_out = command.__tango_command__[1][1][1]
        self.assertEqual(command.func_name, katcpname2tangoname(req_name),
                'The command name is not tango format as expected')
        if with_parameters:
            self.assertEqual(doc_in, req_doc)
            self.assertEqual(doc_out, '')
        else:
            self.assertEqual(doc_in, 'No input parameters')
            self.assertEqual(doc_out, req_doc)

    def test_commad_handler_with_inputs(self):
        req = 'add-result'
        # The command handler at these instance checks for the presence of the
        # word Parameters in the doc string of the request to create a command
        # handler with request parameters.
        req_doc = 'Parameters are x and y'
        self._test_command2request_handler(req, req_doc, with_parameters=True)

    def test_commad_handler_without_inputs(self):
        req = 'time-result'
        req_doc = 'Return the current time in ms since the Unix Epoch'
        self._test_command2request_handler(req, req_doc)

    def _test_command(self, req, expected_result, *args):
        """Testing weather the katcp user defined request can be executed by the Tango
        proxy"""
        sensor_value = self.katcp_server.get_sensor(req)
        self.assertNotEqual(sensor_value.value(), expected_result,
                'The initial value of the sensor is simalar to the test input result')
        command = getattr(self.instance, req.split('-')[0])
        if len(args) > 0:
            reply = command(map(str, *args))
        else:
            reply = command()
        self.assertEqual(reply[0], 'ok', 'Request unsuccessful')
        sensor_value = self.katcp_server.get_sensor(req)
        self.assertEqual(sensor_value.value(),
                getattr(self.device, katcpname2tangoname(req)),
                'Sensor value does not match attribute value after executing a command.')

    def test_add_command(self):
        req = 'add-result'
        input_x = 8.0
        input_y = 8.0
        expected_result = input_x + input_y
        self._test_command(req, expected_result, [input_x, input_y])

    def test_time_command(self):
        req = 'time-result'
        expected_result = 99999.0

        with mock.patch('mkat_tango.translators.tests.test_tango_katcp_proxy.time.time'
                        ) as mock_time:
            mock_time.return_value = expected_result
            self._test_command(req, expected_result)
