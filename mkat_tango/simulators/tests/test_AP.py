###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
Tango Device AP simulator test cases.
"""
from __future__ import absolute_import, division, print_function

import time
import unittest

import mock

from future import standard_library
from mkat_tango.simulators import AntennaPositionerDS
from tango.test_context import DeviceTestContext

standard_library.install_aliases()





class AntennaPositionerTestCase(unittest.TestCase):
    """Test case for the Antenna Positioner device server"""

    device = AntennaPositionerDS.AntennaPositioner

    @classmethod
    def setUpClass(cls):
        cls.tango_context = DeviceTestContext(cls.device)
        cls.tango_context.start()

    def setUp(self):
        """Setting up server instance and update period patcher"""
        update_period_patcher = mock.patch(
            AntennaPositionerDS.__name__ + ".AntennaPositioner.UPDATE_PERIOD"
        )
        self.addCleanup(update_period_patcher.stop)
        update_period_patcher.start()
        AntennaPositionerDS.AntennaPositioner.UPDATE_PERDIOD = 0.1
        super(AntennaPositionerTestCase, self).setUp()

        self.tango_dp = self.tango_context.device
        self.device_server_instance = AntennaPositionerDS.AntennaPositioner.instances[
            self.tango_dp.name()
        ]
        self.az_state = self.device_server_instance.azimuth_quantities
        self.el_state = self.device_server_instance.elevation_quantities

    def tearDown(self):
        """Destroying the AP device server instance"""
        self.device_server_instance = None

    @classmethod
    def tearDownClass(cls):
        """Kill the device server."""
        cls.tango_context.stop()

    def test_attribute_values(self):
        """Simple test cases for initial device attributes values"""
        self.assertEqual(self.tango_dp.requested_mode, "stop")
        self.assertEqual(self.tango_dp.requested_azimuth, 0.0)
        self.assertEqual(self.tango_dp.requested_elevation, 90.0)
        self.assertEqual(self.tango_dp.actual_mode, "stop")
        self.assertEqual(self.tango_dp.actual_azimuth, 0.0)
        self.assertEqual(self.tango_dp.actual_elevation, 90.0)
        self.assertEqual(self.tango_dp.requested_azimuth_rate, 0.0)
        self.assertEqual(self.tango_dp.requested_elevation_rate, 0.0)

    def test_active_threads(self):
        """Testing of active threads running the device"""
        self.assertEqual(
            self.device_server_instance.azimuth_quantities["running"].is_set(), True
        )
        self.assertEqual(
            self.device_server_instance.elevation_quantities["running"].is_set(), True
        )

    def _write_coordinate_attributes(self, desired_az, desired_el):
        """Method for setting desired values to writable coordinate attributes"""
        self.assertNotEqual(self.az_state["requested"][0], desired_az)
        self.assertNotEqual(self.el_state["requested"][0], desired_el)
        self.tango_dp.requested_azimuth = desired_az
        self.tango_dp.requested_elevation = desired_el
        self.assertEqual(self.az_state["requested"][0], desired_az)
        self.assertEqual(self.el_state["requested"][0], desired_el)

    def _write_velocity_attributes(self, desired_az_rate, desired_el_rate):
        """Method for setting desired values to writable velocity attributes """
        self.assertNotEqual(self.az_state["drive_rate"], desired_az_rate)
        self.assertNotEqual(self.el_state["drive_rate"], desired_el_rate)
        self.tango_dp.requested_azimuth_rate = desired_az_rate
        self.tango_dp.requested_elevation_rate = desired_el_rate
        self.assertEqual(self.az_state["drive_rate"], desired_az_rate)
        self.assertEqual(self.el_state["drive_rate"], desired_el_rate)

    def _read_coordinate_attributes(self, desired_az, desired_el):
        """Method for checking actual values of readable attributes"""
        self.assertEqual(self.az_state["actual"][0], desired_az)
        self.assertEqual(self.el_state["actual"][0], desired_el)

    def test_write_coordinate_attributes(self):
        """Checking if the coordinate attributes are
           assigned their values correctly"""
        self._write_coordinate_attributes(-20.0, 70.0)

    def test_write_velocity_attribute(self):
        """Checking if the velocity attributes are
           assigned their values correctly"""
        self._write_velocity_attributes(0.5, 0.5)

    def _wait_finish(self, timeout=5):
        """Returns true when finished updating"""
        start = time.time()
        stop = start + timeout  # timeout after 10 seconds
        while (
            self.az_state["actual"][0] != self.az_state["requested"][0]
            or self.el_state["actual"][0] != self.el_state["requested"][0]
        ):
            if time.time() > stop:
                return False
            time.sleep(0.1)
        return True

    def test_slew_simulation(self):
        """Testing if slew commands provides correct request"""
        actual_az = self.tango_dp.actual_azimuth
        actual_el = self.tango_dp.actual_elevation
        desired_az = actual_az - 1
        desired_el = actual_el - 1
        self._write_velocity_attributes(1.0, 1.0)
        self._write_coordinate_attributes(desired_az, desired_el)
        self.tango_dp.slew()
        self.assertEqual(self.tango_dp.requested_mode, "slew")
        self.assertEqual(self._wait_finish(3), True)
        self._read_coordinate_attributes(desired_az, desired_el)
        self.assertEqual(self.tango_dp.actual_mode, "stop")

    def test_stop_simulation(self):
        """Testing if the stop command halt the AP movement"""
        actual_az = self.tango_dp.actual_azimuth
        actual_el = self.tango_dp.actual_elevation
        desired_az = actual_az - 10.0
        desired_el = actual_el - 10.0
        self._write_velocity_attributes(0.5, 0.5)
        self._write_coordinate_attributes(desired_az, desired_el)
        self.tango_dp.slew()
        self.assertEqual(self.tango_dp.requested_mode, "slew")
        self.tango_dp.Stop()
        self.assertEqual(self.tango_dp.actual_mode, "stop")

    def test_stow_simulation(self):
        """Testing if the stow command puts the AP to it's initial state"""
        self.test_slew_simulation()
        self.tango_dp.stow()
        self.assertEqual(self.tango_dp.requested_mode, "stow")
        self.assertEqual(self._wait_finish(3), True)
        self._read_coordinate_attributes(0.0, 90.0)
        self.assertEqual(self.tango_dp.actual_mode, "stop")
