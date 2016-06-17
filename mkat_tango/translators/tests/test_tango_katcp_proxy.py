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
import unittest2 as unittest
import time
import logging
import tornado
from mock import Mock

from katcp import Sensor, kattypes
from katcp import DeviceServer, Sensor, ProtocolFlags, AsyncReply
from katcp.kattypes import (Str, Float, Timestamp, Discrete,
                            request, return_reply)
from katcp.testutils import start_thread_with_cleanup

from katproxy.sim.mkat_ap import MkatApModel

from mkat_tango.translators.tango_katcp_proxy import (TangoDeviceServer,
                                                      update_tango_server_attribute_list,
                                                      kattype2tangotype_object,
                                                      KatcpTango2DeviceProxy)
from mkat_tango.translators.tango_inspecting_client import TangoInspectingClient
from mkat_tango.translators.katcp_tango_proxy import (tango_attr_descr2katcp_sensor,
                                                     is_tango_device_running)
from mkat_tango.translators.utilities import katcpname2tangoname, tangoname2katcpname
from devicetest import DeviceTestCase

logger = logging.getLogger(__name__)

sensor_list = {
        'failure-present': Sensor(Sensor.BOOLEAN, "failure-present",
                   "Indicates whether at least one failure that prevents antenna "
                   "movement is currently latched", ""),
        'reboot-reason': Sensor(Sensor.DISCRETE, "reboot-reason",
                   "Reports reason for last reboot of the ACU",
                   "", ['powerfailure', 'plc-watchdog', 'remote', 'other']),
        'actual-azim': Sensor(Sensor.FLOAT, "actual-azim", "Actual azimuth position",
                   "deg", [-185.0, 275.0]),
        'track-stack-size': Sensor(Sensor.INTEGER, "track-stack-size",
                   "The number of track samples available in the ACU sample stack",
                   "", [0, 3000]),
        'gps-nmea': Sensor(Sensor.STRING, "gps-nmea", "GPS NMEA string details received", ""),
        'ntp-addr2': Sensor(Sensor.TIMESTAMP, "ntp-addr2", "NTP server IP address", "", [0, 100000.00]),
        'ntp-addr4': Sensor(Sensor.ADDRESS, "ntp-addr4", "NTP server IP address", ""),
        'ntp-addr5': Sensor(Sensor.LRU, "ntp-addr5", "NTP server IP address", "")}

default_attributes = {'state': 'State', 'status': 'Status'}

server_host = "localhost"
server_port = 53020

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
        for sensor in sensor_list.values():
            self.add_sensor(sensor)

class test_KatcpTango2DeviceProxy(DeviceTestCase):

    device = TangoDeviceServer
    properties = dict(katcp_address=server_host + ':' + str(server_port))

    def setUp(self):
        super(test_KatcpTango2DeviceProxy, self).setUp()
        self.instance = TangoDeviceServer.instances[self.device.name()]
        self.katcp_server = KatcpTestDevice(server_host, server_port)
        start_thread_with_cleanup(self, self.katcp_server)
        self.instance.katcp_tango_proxy.katcp_inspecting_client.katcp_client.wait_protocol(timeout=2)
        def cleanup_refs():
            del self.instance
        self.addCleanup(cleanup_refs)
        # Need to reset the device server to its default configuration
        self.addCleanup(update_tango_server_attribute_list,
                        self.instance, sensor_list, remove_attr=True)

    def test_update_tango_server_attribute_list(self):
        """Testing that the update_tango_server_attribute_list method works correctly.
        """
        # Get the initial attributes of the device server
        device_attrs = set(list(self.device.get_attribute_list()))
        default_attrs = set(default_attributes.values())
        self.assertEquals(device_attrs, default_attrs, "The device server"
                          " has unexpected default attributes")
        update_tango_server_attribute_list(self.instance, sensor_list)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertNotEquals(device_attrs, default_attrs,
                             "Attribute list was never updated")
        # Test if the number of attributes has increased after the update
        self.assertGreater(len(device_attrs), len(default_attrs),
                           "Attribute list was never updated")
        # Test if its possible to remove attributes from the device server.
        update_tango_server_attribute_list(self.instance, sensor_list, remove_attr=True)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertEquals(device_attrs, default_attrs, "The device server"
                          " has unexpected default attributes")

    def test_expected_sensor_attributes(self):
        """Testing if the expected attribute list matches with the actual attribute list
           after adding the new attributes.
        """
        default_device_sens = self._create_default_sensors()
        attr_list = set(list(self.device.get_attribute_list()))
        default_attrs = set(default_attributes.values())
        self.assertEquals(attr_list, default_attrs, "The device server"
                          " has unexpected default attributes")
        update_tango_server_attribute_list(self.instance, sensor_list)
        attr_list = set(list(self.device.get_attribute_list()))
        sens_list = sensor_list.copy()
        sens_list.update(default_device_sens)
        sens_list_names = []
        for sen in sens_list:
            sens_list_names.append(katcpname2tangoname(sens_list[sen].name))
        self.assertEqual(attr_list, set(sens_list_names), "The attribute list and the "
                         "the sensor list do not match")

    def _create_default_sensors(self):
        """
        """
        tango_insp_client = Mock(wraps=TangoInspectingClient(self.device))
        def_attrs = tango_insp_client.inspect_attributes()
        def_sens = {}
        attr2sens = Mock(side_effect=tango_attr_descr2katcp_sensor)
        for attrs_desc in def_attrs.keys():
            def_sens[attrs_desc] = attr2sens(def_attrs[attrs_desc])
        return def_sens


    def test_attribute_sensor_properties_match(self):
        """ Testing if the sensor object properties were translated correctly
        """
        default_device_sens = self._create_default_sensors()
        attr_list = set(list(self.device.get_attribute_list()))
        default_attrs = set(default_attributes.values())
        self.assertEquals(attr_list, default_attrs, "The device server"
                          " has unexpected default attributes")
        update_tango_server_attribute_list(self.instance, sensor_list)
        sens_list = sensor_list.copy()
        sens_list.update(default_device_sens)

        for sensor in sens_list.values():
            attr_desc = self.device.get_attribute_config(katcpname2tangoname(sensor.name))
            self.assertEqual(tangoname2katcpname(attr_desc.name), sensor.name,
                             "The sensor and the attribute name are not the same")
            self.assertEqual(attr_desc.description, sensor.description,
                             "The sensor and the attribute description are not identical")
            self.assertEqual(attr_desc.unit, sensor.units,
                             "The sensor and the attribute unit are not identical")
            if sensor.stype in ['integer']:
                self.assertEqual(int(attr_desc.min_value), sensor.params[0],
                                 "The sensor and attribute min values are not identical")
                self.assertEqual(int(attr_desc.max_value), sensor.params[1],
                                 "The sensor and attribute max values are not identical")
            elif sensor.stype in ['float']:
                self.assertEqual(float(attr_desc.min_value), sensor.params[0],
                                 "The sensor and attribute min values are not identical")
                self.assertEqual(float(attr_desc.max_value), sensor.params[1],
                                 "The sensor and attribute max values are not identical")
            # TODO (KM) 14-06-2016: Need to check the params for the discrete sensor type
                                 # once solution for DevEnum is found.
            elif sensor.stype == 'string':
                self.assertEqual(attr_desc.min_value, "Not specified",
                                 "The string sensor type object has unexpected min_value")
                self.assertEqual(attr_desc.max_value, "Not specified",
                                 "The string sensor type object has unexpected min_value")
                self.assertEqual(sensor.params, [],
                                 "The sensor object has a non-empty params list")


    def test_connections(self):
        """Testing if both the TANGO client proxy and the KATCP inspecting clients
        have established a connection with their device servers, respectively.
        """
        is_proxy_connecting_to_server = is_tango_device_running(self.device)
        self.assertEqual(is_proxy_connecting_to_server, True, "No connection established"
                         " between client and server")
        self.assertEqual(self.instance.katcp_tango_proxy.katcp_inspecting_client.is_connected(), True, "The KATCP inspecting client"
                        " is not connected to the device server")


     # TODO (KM 2016-06-17) : Need to check for config changes on the tango device server
#class test_KatcpTango(DeviceTestCase, tornado.testing.AsyncTestCase):
#
#    device = TangoDeviceServer
#    properties = dict(katcp_address=server_host + ':' + str(server_port))
#
#    def setUp(self):
#        super(test_KatcpTango, self).setUp()
#        self.instance = TangoDeviceServer.instances[self.device.name()]
#        self.katcp_server = KatcpTestDevice(server_host, server_port)
#        if hasattr(self, 'io_loop'):
#            self.DUT.set_ioloop(self.io_loop)
#            self.io_loop.add_callback(self.katcp_server.start)
#            self.addCleanup(self.DUT.stop, timeout=None)
#        else:
#            start_thread_with_cleanup(self, self.katcp_server)
#        self.instance.katcp_tango_proxy.katcp_inspecting_client.katcp_client.wait_protocol(timeout=2)
#        def cleanup_refs():
#            del self.instance
#        self.addCleanup(cleanup_refs)
#        # Need to reset the device server to its default configuration
#        self.addCleanup(update_tango_server_attribute_list,
#                        self.instance, sensor_list, remove_attr=True)
#
#
#    @tornado.gen.coroutine
#    def test_attribute_list_updates(self):
#        """Testing if the KATCP device state updates reflect in the TANGO device
#        configuration.
#        """
#        #time.sleep(3)
#        initial_tango_dev_attr_list = set(list(self.device.get_attribute_list()))
#        #print initial_tango_dev_attr_list
#        #import IPython; IPython.embed()
#        #assert the sensor is in the katcp device and tango device
#        self.katcp_server.remove_sensor('failure-present')
#        yield self.instance.katcp_tango_proxy.katcp_inspecting_client.until_synced()
#        self.assertNotIn('failure-present', self.katcp_server.get_sensors())
#        #time.sleep(10)
#        current_tango_dev_attr_list = set(list(self.device.get_attribute_list()))
#        #print current_tango_dev_attr_list


