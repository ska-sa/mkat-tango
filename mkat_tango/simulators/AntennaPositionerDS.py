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
Tango Device AP simulator.
"""
import time
import numpy
import threading

from PyTango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from PyTango.server import Device, DeviceMeta, attribute, command, server_run
from PyTango.server import device_property

class AntennaPositioner(Device):
	'''Antenna Positioner device server with simulated attributes'''
	__metaclass__ = DeviceMeta

	def __init__(self, *args, **kwargs):
		super(AntennaPositioner, self).__init__(*args, **kwargs)
		self._requested_azimuth = (0.0, 0, AttrQuality.ATTR_VALID)
		self._actual_azimuth = (0.0, 0, AttrQuality.ATTR_VALID)
		self.set_change_event('actual_azimuth', True)
		self._requested_elevation = (0.0, 0, AttrQuality.ATTR_VALID)
		self._actual_elevation = (0.0, 0, AttrQuality.ATTR_VALID)
		self.set_change_event('actual_elevation', True)
		
	def init_device(self):
		super(AntennaPositioner, self).init_device()
		self.set_state(DevState.STANDBY)

	@attribute(label="Requested Azimuth of AP", dtype=float)
	def requested_azimuth(self):
		return self._requested_azimuth
		
	@requested_azimuth.setter
	def requested_azimuth(self, azimuth, timestamp=time.time()):
		self._requested_azimuth = (azimuth, timestamp, AttrQuality.ATTR_VALID)

	@attribute(label="Actual Azimuth of AP", dtype=float, abs_change=0.05)
	def actual_azimuth(self):
		return self._actual_azimuth

	@attribute(label="Requested Elevation of AP", dtype=float)
	def requested_elevation(self):
		return self._requested_elevation

	@requested_elevation.setter
	def requested_elevation(self, elevation, timestamp=time.time()):
		self._requested_elevation = (elevation, timestamp, AttrQuality.ATTR_VALID)

	@attribute(label="Actual Elevation of AP", dtype=float, abs_change=0.05)
	def actual_elevation(self):
		return self._actual_elevation

	@command
	def TurnOn(self):
		'''turn on the actual power supply here'''
		self.set_state(DevState.ON)

	@command
	def TurnOff(self):
		'''turn off the actual power supply here'''
		self.set_state(DevState.OFF)
		
if __name__ == "__main__":
	server_run([AntennaPositioner])
