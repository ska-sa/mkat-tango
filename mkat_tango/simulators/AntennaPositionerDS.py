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
import sys
import time
import threading
import logging
import weakref

from functools import partial

from PyTango.server import Device, DeviceMeta, attribute, command, server_run

from PyTango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt

#Module logger reporting events that occur during normal operation of device
LOGGER = logging.getLogger(__name__)

class AntennaPositioner(Device):
    '''Antenna Positioner device server with simulated attributes'''
    __metaclass__ = DeviceMeta

    #Access instances for debugging
    instance = weakref.Weakref.WeakValueDictionary()

    UPDATE_PERIOD = 1
    AZIM_DRIVE_MAX_RATE = 2.0
    ELEV_DRIVE_MAX_RATE = 1.0

    def __init__(self, *args, **kwargs):
        '''Initialize attribute values and change events for update'''
        valid = AttrQuality.ATTR_VALID
        self.azimuth_quantities = dict(actual=(0.0, 0, valid),
                                    requested=(0.0, 0, valid),
                                    drive_rate=0.0, moving=False,
									running=threading.Event())
        self.elevation_quantities = dict(actual=(90.0, 0, valid),
                                    requested=(90.0, 0, valid),
                                    drive_rate=0.0, moving=False,
									running=threading.Event())
        super(AntennaPositioner, self).__init__(*args, **kwargs)
        self.set_change_event('actual_azimuth', True)
        self.set_change_event('actual_elevation', True)

    def init_device(self):
        '''Initialize device and set the state to standby'''
        super(AntennaPositioner, self).init_device()
		name = self.get_name()
		self.instance[name] = self
        self.set_state(DevState.STANDBY)
        self._mode = 'stop', 0, AttrQuality.ATTR_VALID
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
        return self._mode

    @mode.write
    def mode(self, new_mode, valid=AttrQuality.ATTR_VALID):
        if self._mode[0] != new_mode:
            self._mode = new_mode, time.time(), valid

    @attribute(label="Requested Azimuth position of AP", min_value=-185.0,
                max_value=275.0, dtype=float, unit='deg')
    def requested_azimuth(self):
        return self.azimuth_quantities['requested']

    @requested_azimuth.write
    def requested_azimuth(self, azimuth, timestamp=time.time):
        valid = AttrQuality.ATTR_VALID
        self.azimuth_quantities['requested'] = (azimuth, timestamp(), valid)

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
        valid = AttrQuality.ATTR_VALID
        self.elevation_quantities['requested'] = (elevation, timestamp(), valid)

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
        running = sim_quantities['running']
        running.set()
        time_func = time.time
        last_update_time = time_func()

        while running.is_set():
            if self._mode[0] == 'stop' and sim_quantities['moving'] == False:
                time.sleep(self.UPDATE_PERIOD)
                continue
            else:
                last_update_time = time_func()
                time.sleep(self.UPDATE_PERIOD)
                pass

            sim_time = time_func()
            self._mode = 'point', time_func(), AttrQuality.ATTR_VALID
            sim_quantities['moving'] = True
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
                self.push_change_event(attr_name, new_position, sim_time,
                                       quality)
                LOGGER.info("Stepping at {} for {}, requested: {} & actual: {}"
                          .format(sim_time, attr_name, requested, new_position))
            except Exception:
                LOGGER.debug('Exception in update loop', exc_info=True)
            if self.almost_equal(sim_quantities['requested'][0],
                              sim_quantities['actual'][0]):
                if self._mode[0] == 'point':
                    sim_quantities['moving'] = False
                    self._update_moving()

    def _update_moving(self):
        '''Checkes the motion flag of both el-az coordinates if false
               and then sets the AP mode to stop'''
        if (self.azimuth_quantities['moving'] == False and
             self.elevation_quantities['moving'] == False):
            self._mode = 'stop', time.time(), AttrQuality.ATTR_VALID

    @command
    def Slew(self):
        '''Set the simulator operation mode to slew to desired coordinates.'''
        self._mode = 'slew', time.time(), AttrQuality.ATTR_VALID

    @command
    def Stop(self):
        '''Stop the Antenna Positioner instantly'''
        self._mode = 'stop', time.time(), AttrQuality.ATTR_VALID

    @command
    def Stow(self):
        '''Stow/Park the AP to its intitial state of operation'''
        time_func = time.time
        valid = AttrQuality.ATTR_VALID
        self.azimuth_quantities['drive_rate'] = self.AZIM_DRIVE_MAX_RATE
        self.elevation_quantities['drive_rate'] = self.ELEV_DRIVE_MAX_RATE
        self.azimuth_quantities['requested'] = (0.0, time_func(), valid)
        self.elevation_quantities['requested'] = (90.0, time_func(), valid)
        self._mode = 'stow', time_func(), valid

if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s-%(pathname)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    server_run([AntennaPositioner])
