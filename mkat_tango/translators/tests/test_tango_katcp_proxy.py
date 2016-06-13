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
import weakref

from katproxy.sim.mkat_ap import MkatApModel

from mkat_tango.translators.tango_katcp_proxy import (TangoDeviceServer,
                                                      update_tango_server_attribute_list)
from devicetest import DeviceTestCase


logger = logging.getLogger(__name__)

ap_model = MkatApModel()

class test_KatcpTango2DeviceProxy(DeviceTestCase):

    external = False
    device = TangoDeviceServer


    def setUp(self):
        super(test_KatcpTango2DeviceProxy, self).setUp()
        self.instance = TangoDeviceServer.instances[self.device.name()]
        def cleanup_refs(): del self.instance
        self.addCleanup(cleanup_refs)

    def test_update_tango_server_attribute_list(self):
        #Get the initial attributes of the device server
        device_attrs = set(list(self.device.get_attribute_list()))
        default_attributes = frozenset(['State', 'Status'])
        self.assertEquals(device_attrs, default_attributes, "The device server"
                          " has more than two default attributes")
        sensor_list = ap_model.get_sensors()
        update_tango_server_attribute_list(self.instance, sensor_list)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertNotEquals(device_attrs, default_attributes,
                             "Attribute list was never updated")
        #Test if the number of attributes has increased after the update
        self.assertGreater(len(device_attrs), len(default_attributes),
                           "Attribute list was never updated")
        #Test if its possible to remove attributes from the device server.
        update_tango_server_attribute_list(self.instance, sensor_list, remove_attr=True)
        device_attrs = set(list(self.device.get_attribute_list()))
        self.assertEquals(device_attrs, default_attributes, "The device server"
                          " has more than two default attributes")
