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

	UPDATE_PERIOD = 1
	AZIM_DRIVE_MAX_RATE = 2.0
	ELEV_DRIVE_MAX_RATE = 1.0

	def __init__(self, *args, **kwargs):
		super(AntennaPositioner, self).__init__(*args, **kwargs)
		self._requested_azimuth = (0.0, 0, AttrQuality.ATTR_VALID)
		self._actual_azimuth = (0.0, 0, AttrQuality.ATTR_VALID)
		self.set_change_event('actual_azimuth', True)
		self._requested_elevation = (90.0, 0, AttrQuality.ATTR_VALID)
		self._actual_elevation = (90.0, 0, AttrQuality.ATTR_VALID)
		self.set_change_event('actual_elevation', True)
		self._mode = "stop"

	def init_device(self):
		super(AntennaPositioner, self).init_device()
		self.set_state(DevState.STANDBY)

	@attribute(label="Current operational mode of the AP", dtype=str)
	def mode(self):
		return self._mode

	@mode.setter
	def mode(self, newmode):
		self._mode = newmode

	@attribute(label="Requested Azimuth position of AP", min_value=-185.0,
				max_value=275.0, dtype=float)
	def requested_azimuth(self):
		return self._requested_azimuth

	@requested_azimuth.setter
	def requested_azimuth(self, azimuth, timestamp=time.time()):
		self._requested_azimuth = (azimuth, timestamp, AttrQuality.ATTR_VALID)

	@attribute(label="Actual Azimuth position of AP", dtype=float,
				min_value=-185.0, max_value=275.0, abs_change=0.05)
	def actual_azimuth(self):
		return self._actual_azimuth

	@attribute(label="Requested Elevation position of AP", min_value=15.0,
				max_value=92.0, dtype=float)
	def requested_elevation(self):
		return self._requested_elevation

	@requested_elevation.setter
	def requested_elevation(self, elevation, timestamp=time.time()):
		self._requested_elevation = (elevation, timestamp, AttrQuality.ATTR_VALID)

	@attribute(label="Actual Elevation position of AP", dtype=float,
				min_value=15.0, max_value=92.0, abs_change=0.05)
	def actual_elevation(self):
		return self._actual_elevation

	@attribute(label="Actual azimuth velocity", dtype=float,
				min_value=-AZIM_DRIVE_MAX_RATE, max_value=AZIM_DRIVE_MAX_RATE)
	def actual_azimuth_rate(self):
		return self._actual_azimuth_rate

	@actual_azimuth_rate.setter
	def actual_azimuth_rate(self, rate):
	# Limit the rate to the maximum allowed
		if rate > self.AZIM_DRIVE_MAX_RATE:
			rate = self.AZIM_DRIVE_MAX_RATE
		elif rate < -self.AZIM_DRIVE_MAX_RATE:
			rate = -self.AZIM_DRIVE_MAX_RATE
		else:
			pass
		self._actual_azimuth_rate = rate

	@attribute(label="Actual elevation velocity", dtype=float,
				min_value=-ELEV_DRIVE_MAX_RATE, max_value=ELEV_DRIVE_MAX_RATE)
	def actual_elevation_rate(self):
		return self._actual_elevation_rate

	@actual_elevation_rate.setter
	def actual_elevation_rate(self, rate):
	# Limit the rate to the maximum allowed
		if rate > self.ELEV_DRIVE_MAX_RATE:
			rate = self.ELEV_DRIVE_MAX_RATE
		elif rate < -self.ELEV_DRIVE_MAX_RATE:
			rate = -self.ELEV_DRIVE_MAX_RATE
		else:
			pass
		self._actual_elevation_rate = rate

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
