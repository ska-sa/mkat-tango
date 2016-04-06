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

#Module logger reporting events that occur during normal operation of device
LOGGER = logging.getLogger(__name__)

class AntennaPositioner(Device):
    '''Antenna Positioner device server with simulated attributes'''
    __metaclass__ = DeviceMeta

    UPDATE_PERIOD = 1
    AZIM_DRIVE_MAX_RATE = 2.0
    ELEV_DRIVE_MAX_RATE = 1.0

    def __init__(self, *args, **kwargs):
        '''Initialize attribute values and change events for update'''
        self._moving = dict(actual_azimuth=False, actual_elevation=False)
        attr = AttrQuality.ATTR_VALID
        self.azimuth_quantities = dict(actual=(0.0, 0, attr),
                                    requested=(0.0, 0, attr),
                                    drive_rate=0.0)
        self.elevation_quantities = dict(actual=(90.0, 0, attr),
                                    requested=(90.0, 0, attr),
                                    drive_rate=0.0)
        super(AntennaPositioner, self).__init__(*args, **kwargs)
        self.set_change_event('actual_azimuth', True)
        self.set_change_event('actual_elevation', True)
    def init_device(self):
        '''Initialize device and set the state to standby'''
        super(AntennaPositioner, self).init_device()
        self.set_state(DevState.STANDBY)
        self.Mode = 'stop', 0, AttrQuality.ATTR_VALID
        self.azimuth_update = partial(
            self.update_position, 'actual_azimuth', self.azimuth_quantities)
        self.elevation_update = partial(
            self.update_position, 'actual_elevation', self.elevation_quantities)

        self.az_thread = threading.Thread(target=self.azimuth_update)
        self.el_thread = threading.Thread(target=self.elevation_update)
        self.az_thread.setDaemon(True)
        self.el_thread.setDaemon(True)
        self.az_thread.start()
        self.el_thread.start()

    #ATTRIBUTES

    @attribute(label="Current operational mode of the AP", dtype=str)
    def mode(self):
        return self.Mode

    @mode.write
    def mode(self, new_mode, attr = AttrQuality.ATTR_VALID):
        current_mode = self.Mode
        if current_mode != new_mode:
            self.Mode = new_mode, attr

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
        self.azimuth_quantities['drive_rate'] = rate

    @attribute(label="Requested elevation velocity", dtype=float, unit='deg/s',
                min_value=-ELEV_DRIVE_MAX_RATE, max_value=ELEV_DRIVE_MAX_RATE)
    def requested_elevation_rate(self):
        return self.elevation_quantities['drive_rate']

    @requested_elevation_rate.write
    def requested_elevation_rate(self, rate):
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

    def almost_equal(self, x, y, abs_threshold=1e-2):
        '''Takes two values return true if they are almost equal'''
        return abs(x - y) <= abs_threshold

    def update_position(self, attr_name, sim_quantities):
        '''Updates the position of the el-az coordinates
              using a simulation loop'''
        actual_position = sim_quantities['actual']
        requested_position = sim_quantities['requested']
        time_func = time.time
        last_update_time = time_func()
        while True:
            if not self._moving[attr_name]:
                last_update_time = time_func()
                self.Mode = 'stop', time_func(), AttrQuality.ATTR_VALID
                time.sleep(self.UPDATE_PERIOD)
                continue
            sim_time = time_func()
            self.Mode = 'point', time_func(), AttrQuality.ATTR_VALID
            dt = sim_time - last_update_time
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
                last_update_time = sim_time
                self.push_change_event(attr_name,  new_position, sim_time, quality)
                LOGGER.info("Stepping at {} for {}, requested: {} & actual: {}"
                           .format(sim_time, attr_name, requested, new_position))
            except Exception:
                LOGGER.debug('Exception in update loop')
            if self.almost_equal(sim_quantities['requested'][0],
                   sim_quantities['actual'][0]):
                if self.Mode[0] == 'point':
                    self._moving[attr_name] = False
                    if (self._moving['actual_azimuth'] == False and
                        self._moving['actual_elevation'] == False):
                        self.Mode = 'stop', time_func(), AttrQuality.ATTR_VALID
            time.sleep(self.UPDATE_PERIOD)

    @command
    def Slew(self):
        '''Set the simulator operation mode to slew to desired coordinates.'''
        self._moving['actual_azimuth'] = True
        self._moving['actual_elevation'] = True
        self.Mode = 'slew', time.time(), AttrQuality.ATTR_VALID

    @command
    def Stop(self):
        '''Stop the Antenna PositioneR instantly'''
        self._moving['actual_azimuth'] = False
        self._moving['actual_elevation'] = False
        self.Mode = 'stop', time.time(), AttrQuality.ATTR_VALID

    @command
    def Stow(self):
        '''Stow/Park the AP to its intitial state of operation'''
        time_func = time.time
        attr = AttrQuality.ATTR_VALID
        self.azimuth_quantities['drive_rate'] = self.AZIM_DRIVE_MAX_RATE
        self.elevation_quantities['drive_rate'] = self.ELEV_DRIVE_MAX_RATE
        self.azimuth_quantities['requested'] = (0.0, time_func(), attr)
        self.elevation_quantities['requested'] = (90.0, time_func(), attr)
        self._slewing['actual_azimuth'] = True
        self._slewing['actual_elevation'] = True
        self.mode = 'stow', time_func(), attr

if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s-%(pathname)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    server_run([AntennaPositioner])
