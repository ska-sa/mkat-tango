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
from mock import Mock

from katcp import Sensor, kattypes

from katproxy.sim.mkat_ap import MkatApModel

from mkat_tango.translators.tango_katcp_proxy import (TangoDeviceServer,
                                                      update_tango_server_attribute_list,
                                                      kattype2tangotype_object)
from mkat_tango.translators.tango_inspecting_client import TangoInspectingClient
from mkat_tango.translators.katcp_tango_proxy import tango_attr_descr2katcp_sensor
from mkat_tango.translators.utilities import katcpname2tangoname, tangoname2katcpname
from devicetest import DeviceTestCase

logger = logging.getLogger(__name__)

sensor_list = [
        Sensor(Sensor.BOOLEAN, "failure-present",
                   "Indicates whether at least one failure that prevents antenna "
                   "movement is currently latched", ""),
        Sensor(Sensor.DISCRETE, "reboot-reason",
                   "Reports reason for last reboot of the ACU",
                   "", ['powerfailure', 'plc-watchdog', 'remote', 'other']),
        Sensor(Sensor.FLOAT, "actual-azim", "Actual azimuth position",
                   "deg", [-185.0, 275.0]),
        Sensor(Sensor.INTEGER, "track-stack-size",
                   "The number of track samples available in the ACU sample stack",
                   "", [0, 3000]),
        Sensor(Sensor.STRING, "gps-nmea", "GPS NMEA string details received", ""),
        Sensor(Sensor.TIMESTAMP, "ntp-addr2", "NTP server IP address", "", [0, 100000.00]),
        Sensor(Sensor.ADDRESS, "ntp-addr4", "NTP server IP address", ""),
        Sensor(Sensor.LRU, "ntp-addr5", "NTP server IP address", "")]

default_attributes = frozenset(['State', 'Status'])

class test_KatcpTango2DeviceProxy(DeviceTestCase):

    device = TangoDeviceServer

    def setUp(self):
        super(test_KatcpTango2DeviceProxy, self).setUp()
        self.instance = TangoDeviceServer.instances[self.device.name()]
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
        self.assertEquals(device_attrs, default_attributes, "The device server"
                          " has unexpected default attributes")
        update_tango_server_attribute_list(self.instance, sensor_list)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertNotEquals(device_attrs, default_attributes,
                             "Attribute list was never updated")
        # Test if the number of attributes has increased after the update
        self.assertGreater(len(device_attrs), len(default_attributes),
                           "Attribute list was never updated")
        # Test if its possible to remove attributes from the device server.
        update_tango_server_attribute_list(self.instance, sensor_list, remove_attr=True)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertEquals(device_attrs, default_attributes, "The device server"
                          " has unexpected default attributes")

    def test_expected_sensor_attributes(self):
        """Testing if the expected attribute list matches with the actual attribute list
           after adding the new attributes.
        """
        default_device_sens = self._create_default_sensors()
        attr_list = set(list(self.device.get_attribute_list()))
        self.assertEquals(attr_list, default_attributes, "The device server"
                          " has unexpected default attributes")
        update_tango_server_attribute_list(self.instance, sensor_list)
        attr_list = set(list(self.device.get_attribute_list()))
        sens_list = sensor_list[:]
        sens_list.extend(default_device_sens)
        sens_list_names = []
        for sen in sens_list:
            sens_list_names.append(katcpname2tangoname(sen.name))
        self.assertEqual(attr_list, set(sens_list_names), "The attribute list and the "
                         "the sensor list do not match")

    def _create_default_sensors(self):
        """
        """
        tango_insp_client = Mock(wraps=TangoInspectingClient(self.device))
        def_attrs = tango_insp_client.inspect_attributes()
        def_sens = []
        attr2sens = Mock(side_effect=tango_attr_descr2katcp_sensor)
        for attrs_desc in def_attrs.keys():
            def_sens.append(attr2sens(def_attrs[attrs_desc]))
        return def_sens


    def test_attribute_sensor_properties_match(self):
        """ Testing if the sensor object properties were translated correctly
        """
        default_device_sens = self._create_default_sensors()
        attr_list = set(list(self.device.get_attribute_list()))
        self.assertEquals(attr_list, default_attributes, "The device server"
                          " has unexpected default attributes")
        update_tango_server_attribute_list(self.instance, sensor_list)
        sens_list = sensor_list[:]
        sens_list.extend(default_device_sens)

        for sensor in sens_list:
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
