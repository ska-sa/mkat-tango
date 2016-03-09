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
import logging

from functools import partial

from PyTango.server import device_property
from PyTango.server import Device, DeviceMeta, attribute, command, server_run

from PyTango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt

class AntennaPositioner(Device):
    '''Antenna Positioner device server with simulated attributes'''
    __metaclass__ = DeviceMeta

    UPDATE_PERIOD = 1
    AZIM_DRIVE_MAX_RATE = 2.0
    ELEV_DRIVE_MAX_RATE = 1.0
    LOGGER = logging.getLogger()

    def __init__(self, *args, **kwargs):
        '''Initialize attribute values and change events for update'''
        super(AntennaPositioner, self).__init__(*args, **kwargs)
        self.set_change_event('actual_azimuth', True)
        self.set_change_event('actual_elevation', True)
        self._mode = 'stop'
        self._slewing = dict(actual_azimuth=False, actual_elevation=False)
        self._last_update_time = 0
        self.azimuth_quantities = dict(actual=(0.0, 0, AttrQuality.ATTR_VALID),
                                    requested=(0.0, 0, AttrQuality.ATTR_VALID),
                                    drive_rate=0.0)
        self.elevation_quantities = dict(actual=(90.0, 0, AttrQuality.ATTR_VALID),
                                    requested=(90.0, 0, AttrQuality.ATTR_VALID),
                                    drive_rate=0.0)

    def init_device(self):
        '''Initialize device and set the state to standby'''
        super(AntennaPositioner, self).init_device()
        self.set_state(DevState.STANDBY)

    #ATTRIBUTES

    @attribute(label="Current operational mode of the AP", dtype=str)
    def mode(self):
        return self._mode

    @attribute(label="Requested Azimuth position of AP", min_value=-185.0,
                max_value=275.0, dtype=float, unit='deg')
    def requested_azimuth(self):
        return self.azimuth_quantities['requested']

    @requested_azimuth.write
    def requested_azimuth(self, azimuth, timestamp=time.time):
        attr = AttrQuality.ATTR_VALID
        self.azimuth_quantities['requested'] = (azimuth, timestamp(), attr)

    @attribute(label="Actual Azimuth position of AP", dtype=float,
                min_value=-185.0, max_value=275.0, abs_change=0.05,
                min_warning=-180.0, max_warning=270.0,
                min_alarm=-184.0, max_alarm=274.0, unit='deg')
    def actual_azimuth(self):
        return self.azimuth_quantities['actual']

    @attribute(label="Requested Elevation position of AP", min_value=15.0,
                max_value=92.0, dtype=float, unit='deg')
    def requested_elevation(self):
        return self.elevation_quantities['requested']

    @requested_elevation.write
    def requested_elevation(self, elevation, timestamp=time.time):
        attr = AttrQuality.ATTR_VALID
        self.elevation_quantities['requested'] = (elevation, timestamp(), attr)

    @attribute(label="Actual Elevation position of AP", dtype=float,
                min_value=15.0, max_value=92.0, abs_change=0.05,
                min_warning=20.0, max_warning=87.0,
                min_alarm=14.0, max_alarm=91.0, unit='deg')
    def actual_elevation(self):
        return self.elevation_quantities['actual']

    @attribute(label="Requested azimuth velocity", dtype=float, unit='deg/s',
                min_value=-AZIM_DRIVE_MAX_RATE, max_value=AZIM_DRIVE_MAX_RATE)
    def requested_azimuth_rate(self):
        return self.azimuth_quantities['drive_rate']

    @requested_azimuth_rate.write
    def requested_azimuth_rate(self, rate):
        '''Limit the rate to the maximum allowed'''
        if rate > self.AZIM_DRIVE_MAX_RATE:
            rate = self.AZIM_DRIVE_MAX_RATE
        elif rate < -self.AZIM_DRIVE_MAX_RATE:
            rate = -self.AZIM_DRIVE_MAX_RATE
        else:
            pass
        self.azimuth_quantities['drive_rate'] = rate

    @attribute(label="Requested elevation velocity", dtype=float, unit='deg/s',
                min_value=-ELEV_DRIVE_MAX_RATE, max_value=ELEV_DRIVE_MAX_RATE)
    def requested_elevation_rate(self):
        return self.elevation_quantities['drive_rate']

    @requested_elevation_rate.write
    def requested_elevation_rate(self, rate):
        '''Limit the rate to the maximum allowed'''
        if rate > self.ELEV_DRIVE_MAX_RATE:
            rate = self.ELEV_DRIVE_MAX_RATE
        elif rate < -self.ELEV_DRIVE_MAX_RATE:
            rate = -self.ELEV_DRIVE_MAX_RATE
        else:
            pass
        self.elevation_quantities['drive_rate'] = rate

    #COMMANDS

    @command
    def TurnOn(self):
        '''turn on the actual power supply here'''
        self.set_state(DevState.ON)

    @command
    def TurnOff(self):
        '''turn off the actual power supply here'''
        self.set_state(DevState.OFF)

    def almost_equal(self, x, y, abs_threshold=1e-1):
        '''Takes two values return true if they are almost equal'''
        return abs(x - y) <= abs_threshold

    def update_position(self, attr_name, sim_quantities):
        '''Updates the position of the el-az coordinates using a simulation loop'''
        actual_position = sim_quantities['actual']
        requested_position = sim_quantities['requested']
        self._slewing[attr_name] = True
        self._last_update_time = time.time()
        while True:
            if not self._slewing[attr_name]:
                time.sleep(self.UPDATE_PERIOD)
                continue

            time.sleep(self.UPDATE_PERIOD)
            sim_time = time.time()
            dt = sim_time - self._last_update_time
            self._mode = 'slew'

            try:
                slew_rate = sim_quantities['drive_rate']
                max_slew = slew_rate*dt
                actual = sim_quantities['actual'][0]
                requested = sim_quantities['requested'][0]
                curr_delta = abs(actual - requested)
                move_delta = min(max_slew, curr_delta)
                new_position = actual + cmp(requested, actual)*move_delta

                quality = AttrQuality.ATTR_VALID
                sim_quantities['actual'] = (new_position, sim_time, quality)
                self._last_update_time = sim_time
                self.push_change_event(attr_name,  new_position, sim_time, quality)
                #Instant printing of the new values. (important for debugging)
                print("Stepping at {}, dt: {}    sim {} requested: {}  actual: {} deg"
                    .format(sim_time, dt, attr_name, requested, new_position))
                print("curr_delta: {curr_delta}, move_delta: {move_delta}".format(**locals()),
                    " max_slew: {max_slew}".format(**locals()))
            except Exception:
                self.LOGGER.exception('Exception in update loop')
            if self.almost_equal(sim_quantities['requested'][0],
                   sim_quantities['actual'][0]):
                self._slewing[attr_name] = False
                self._mode = 'stop'
            time.sleep(self.UPDATE_PERIOD)

    @command
    def Slew(self):
        '''Set the simulator operation mode to slew to desired coordinates.'''
        self.azimuth_update = partial(
            self.update_position, 'actual_azimuth', self.azimuth_quantities)
        self.elevation_update = partial(
            self.update_position, 'actual_elevation', self.elevation_quantities)

        self.az_thread = threading.Thread(target=self.azimuth_update)
        self.az_thread.setDaemon(True)
        self.az_thread.start()
        self.el_thread = threading.Thread(target=self.elevation_update)
        self.el_thread.setDaemon(True)
        self.el_thread.start()

if __name__ == "__main__":
    server_run([AntennaPositioner])
