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

import tornado.testing
import tornado.gen

from katcp import DeviceServer, Sensor, ProtocolFlags, Message
from katcp.resource_client import IOLoopThreadWrapper

from mkat_tango.translators.tango_katcp_proxy import (TangoDeviceServer,
                                                      remove_tango_server_attribute_list,
                                                      add_tango_server_attribute_list)
from mkat_tango.translators.katcp_tango_proxy import is_tango_device_running
from mkat_tango.translators.utilities import katcpname2tangoname, tangoname2katcpname

from devicetest import DeviceTestCase

logger = logging.getLogger(__name__)

sensors = {
        'failure-present': Sensor(Sensor.BOOLEAN, "failure-present",
                   "Indicates whether at least one failure that prevents antenna "
                   "movement is currently latched", ""),
        'reboot-reason': Sensor(Sensor.DISCRETE, "reboot-reason",
                   "Reports reason for last reboot of the ACU",
                   "", ['powerfailure', 'plc-watchdog', 'remote', 'other']),
        'actual-azim': Sensor(Sensor.FLOAT, "actual-azim", "Actual azimuth position",
                   "deg", [-183.32, 275.0], 32.9),
        'track-stack-size': Sensor(Sensor.INTEGER, "track-stack-size",
                   "The number of track samples available in the ACU sample stack",
                   "", [0, 3000]),
        'gps-nmea': Sensor(Sensor.STRING, "gps-nmea", "GPS NMEA string details"
                           " received", ""),
        'ntp-timestamp': Sensor(Sensor.TIMESTAMP, "ntp-timestamp",
                "NTP server timestamp", "", [0.00, 1000000000.00]),
        'ntp-lru': Sensor(Sensor.ADDRESS, "ntp-lru", "NTP server IP address", "")}

default_attributes = {'state': 'State', 'status': 'Status'}

server_host = ""
server_port = 0

class KatcpTestDevice(DeviceServer):

    VERSION_INFO = ("example-api", 1, 0)
    BUILD_INFO = ("example-implementation", 0, 1, "")

    # Optionally set the KATCP protocol version and features. Defaults to
    # the latest implemented version of KATCP, with all supported optional
    # features
    PROTOCOL_INFO = ProtocolFlags(5, 0, set([
        ProtocolFlags.MULTI_CLIENT,
        ProtocolFlags.MESSAGE_IDS,
    ]))

    def setup_sensors(self):
        """Setup some server sensors."""
        for sensor in sensors.values():
            self.add_sensor(sensor)

class test_KatcpTango2DeviceProxy(DeviceTestCase):

    device = TangoDeviceServer

    @classmethod
    def setUpClass(cls):
        cls.katcp_server = KatcpTestDevice(server_host, server_port)
        cls.katcp_server.start()
        address = cls.katcp_server.bind_address
        katcp_server_host, katcp_server_port = address
        cls.properties = dict(katcp_address=katcp_server_host + ':' +
                              str(katcp_server_port))
        super(test_KatcpTango2DeviceProxy, cls).setUpClass()

    def setUp(self):
        super(test_KatcpTango2DeviceProxy, self).setUp()
        self.instance = TangoDeviceServer.instances[self.device.name()]
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
        cls.katcp_server.stop()
        super(test_KatcpTango2DeviceProxy, cls).tearDownClass()

    def test_connections(self):
        """Testing if both the TANGO client proxy and the KATCP inspecting clients
        have established a connection with their device servers, respectively.
        """
        is_proxy_connecting_to_server = is_tango_device_running(self.device)
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
        device_attrs = set(list(self.device.get_attribute_list()))
        default_attrs = set(default_attributes.values())
        self.assertEquals(device_attrs, default_attrs,
                          "The device server has unexpected default attributes")
        add_tango_server_attribute_list(self.instance, sensors)

        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertNotEquals(device_attrs, default_attrs,
                             "Attribute list was never updated")
        # Test if the number of attributes has increased after the update
        self.assertGreater(len(device_attrs), len(default_attrs),
                           "Attribute list was never updated")
        # Test if its possible to remove attributes from the device server.
        remove_tango_server_attribute_list(self.instance, sensors)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertEquals(device_attrs, default_attrs,
                          "The device server has unexpected default attributes")

    def test_expected_sensor_attributes(self):
        """Testing if the expected attribute list matches with the actual attribute list
           after adding the new attributes.
        """
        default_attrs = set(default_attributes.values())
        attr_list = list(self.device.get_attribute_list())
        for def_attr in default_attrs:
            attr_list.remove(def_attr)

        sens_names = sensors.keys()
        sensname2tangoname_list = []
        for sen_name in sens_names:
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
            attr_desc = self.device.get_attribute_config(
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
            attr_desc = self.device.get_attribute_config(
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


    def test_sensor2attr_removal_updates(self):
        """Testing if removing a sensor from the KATCP device server also results in the "
        removal of the equivalent TANGO attribute on the TANGO device server.
        """
        initial_tango_dev_attr_list = set(list(self.device.get_attribute_list()))
        sensor_name = 'failure-present'
        self.assertIn(sensor_name, self.katcp_server._sensors.keys(), "Sensor not in"
                      " list")
        self.assertIn(katcpname2tangoname(sensor_name), initial_tango_dev_attr_list,
                      "The attribute was not removed")
        self.katcp_server.remove_sensor(sensor_name)
        self.katcp_server.mass_inform(Message.inform('interface-changed'))
        self.in_ioloop(self.katcp_ic.until_data_synced)()
        time.sleep(0.5)
        self.device.Status()
        current_tango_dev_attr_list = set(list(self.device.get_attribute_list()))
        self.assertNotIn(katcpname2tangoname(sensor_name), current_tango_dev_attr_list,
                      "The attribute was not removed")

    def test_sensor2attr_addition_updates(self):
        """Testing if adding a sensor to the KATCP device server also results in the "
        addition of the equivalent TANGO attribute on the TANGO device server.
        """
        initial_tango_dev_attr_list = set(list(self.device.get_attribute_list()))
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
        current_tango_dev_attr_list = set(list(self.device.get_attribute_list()))
        self.assertIn(sens.name, self.katcp_server._sensors.keys(),
                      "Sensor was not added to the katcp device server.")
        self.assertIn(katcpname2tangoname(sens.name),
                      current_tango_dev_attr_list,
                      "Attribute was not added to the TANGO device server.")

    def _update_katcp_server_sensor_values(self, katcp_device_server):
        """Method that makes updates to all the katcp device server sensors.

        Input Parameters
        ----------------

        katcp_device_server : KATCP DeviceServer
            The katcp device server for which sensor updates are applied to.

        Returns
        ------

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

    def _wait_for_tango_attribute_to_update(self, attr_name, timeout=1):
        """Keeps polling tango attribute from running device until the a value that
        is not None is found, otherwise timeout error exception is raised.

        Input Parameters
        ----------------

        attr_name : str
            Name of tango attribute name to poll

        """
        stoptime = time.time() + timeout
        value = getattr(self.device, attr_name)
        while value is None:
            value = getattr(self.device, attr_name, None)
            time.sleep(0.025)
            if time.time() > stoptime:
                raise RuntimeError("TimeOutError : Tango device server not configured.")

    def test_sensor_attribute_value_update(self):
        """Testing if the KATCP server sensor updates reflect as attribute
        updates in the Tango device server
        """
        self.test_connections()
        katcp_device_server = self._update_katcp_server_sensor_values(
                self.katcp_server)
        for sensor in katcp_device_server.get_sensors():
            attribute_name = katcpname2tangoname(sensor.name)
            self._wait_for_tango_attribute_to_update(attribute_name)
            attribute_value = getattr(self.device, attribute_name)
            sensor_value = sensor.value()
            if type(sensor_value) is tuple:
                # Address sensor type contains a Tuple contaning (host, port) and
                # mapped to tango DevString type i.e "host:port"
                sensor_value = ':'.join(str(s) for s in sensor_value)
            self.assertEqual(attribute_value, sensor_value)
