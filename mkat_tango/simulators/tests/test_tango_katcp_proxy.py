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
MeerKAT AP simulator.

    @author MeerKAT CAM team <cam@ska.ac.za>
"""
import unittest2 as unittest
import time
import logging
import weakref

from katcp import Sensor
from katproxy.sim.mkat_ap import MkatApModel
from devicetest import DeviceTestCase
from tango_katcp_proxy import TangoDeviceServer, update_tango_server_attribute_list
from PyTango import CmdArgType, DevState, DevFailed

logger = logging.getLogger(__name__)

ap_model = MkatApModel()
ap_model.start()

class TestMkatAp(DeviceTestCase):

    external = False
    device = TangoDeviceServer


    def setUp(self):
        super(TestMkatAp, self).setUp()
        self.instance = TangoDeviceServer.instances[self.device.name()]
        def cleanup_refs(): del self.instance
        self.addCleanup(cleanup_refs)

    def test_update_tango_server_attribute_list(self):
        device_attrs = list(self.device.get_attribute_list())
        default_attributes = ['State', 'Status']
        self.assertEquals(device_attrs, default_attributes, "The device server does not"
                          " have an 'empty' attribute list")
        sensor_list = ap_model.get_sensors()
        update_tango_server_attribute_list(self.instance, sensor_list)
        device_attrs = list(self.device.get_attribute_list())
        self.assertNotEquals(device_attrs, default_attributes, "The device server does not"
                          " have an empty attribute list")



