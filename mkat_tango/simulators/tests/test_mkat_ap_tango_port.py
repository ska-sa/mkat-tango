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
Tests for the MeerKAT Antenna Positioner Simulator.
"""

import unittest2 as unittest
import time
import logging
import threading
import mock
#from katcp import Message, Sensor
#from katcp.testutils import BlockingTestClient, TestLogHandler, TestUtilMixin
#from katproxy.testutils import DualTestMixin
#from katproxy.sim.mkat_ap import MkatApDevice, MkatApTestDevice, MkatApModel
#from katproxy.sim.mkat_ap import Control, Drive, EStopReason

from devicetest import DeviceTestCase 
from mkat_tango.simulators.mkat_ap_tango import MkatAntennaPositioner

#ogging.getLogger("katcp").addHandler(TestLogHandler())

logger = logging.getLogger(__name__)

EXPECTED_SENSOR_LIST = [
    ('actual-azim', 'Actual azimuth position', 'deg', 'float', '-185', '275'),
    ('actual-azim-rate', 'Actual azimuth velocity', 'deg/s', 'float', '-2', '2'),
    ('actual-elev', 'Actual elevation position', 'deg', 'float', '15', '92'),
    ('actual-elev-rate', 'Actual elevation velocity', 'deg/s', 'float', '-1', '1'),
    ('acu-plc-interface-error', 'ACU detected communication error between ACU and PLC', '', 'boolean'),
    ('acu-speed-limited', 'Due to excessive power requirements, the maximum velocities have been reduced', '', 'boolean'),
    ('acu-spline-status', 'Status relating to the number of track samples that are currently available in the ACU stack (green=optimal)', '', 'discrete', 'green', 'yellow', 'red'),
    ('amp-power-cycle-interlocked', 'True if waiting time presently applies because there has been too many power cycles of the main contactor for one of the drives', '', 'boolean'),
    ('azim-amp1-failed', 'Azimuth amplifier 1 or the regeneration resistor reports a problem', '', 'boolean'),
    ('azim-amp2-failed', 'Azimuth amplifier 2 or the regeneration resistor reports a problem', '', 'boolean'),
    ('azim-aux1-mode-selected', 'Azimuth axis auxiliary1 mode activated or not (i.e. azimuth only driven by motor 1', '', 'boolean'),
    ('azim-aux2-mode-selected', 'Azimuth axis auxiliary2 mode activated or not (i.e. azimuth only driven by motor 2', '', 'boolean'),
    ('azim-brake1-failed', 'Azimuth brake 1 release problem occured', '', 'boolean'),
    ('azim-brake2-failed', 'Azimuth brake 2 release problem occured', '', 'boolean'),
    ('azim-brakes-released', 'True if all azimuth axis brakes are released', '', 'boolean'),
    ('azim-emergency-limit-ccw-reached', 'Azimuth axis emergency-limit has been reached in the counterclockwise direction', '', 'boolean'),
    ('azim-emergency-limit-cw-reached', 'Azimuth axis emergency-limit has been reached in the clockwise direction', '', 'boolean'),
    ('azim-emergency2-limit-ccw-reached', 'Azimuth axis emergency2-limit has been reached in the counterclockwise direction', '', 'boolean'),
    ('azim-emergency2-limit-cw-reached', 'Azimuth axis emergency2-limit has been reached in the clockwise direction', '', 'boolean'),
    ('azim-enc-failed', 'Azimuth encoder has failed', '', 'boolean'),
    ('azim-hard-limit-ccw-reached', 'Azimuth axis hard-limit has been reached in the counterclockwise direction', '', 'boolean'),
    ('azim-hard-limit-cw-reached', 'Azimuth axis hard-limit has been reached in the clockwise direction', '', 'boolean'),
    ('azim-motion-error', 'Azimuth axis does not move although commanded to do so', '', 'boolean'),
    ('azim-motor1-current', 'Azimuth motor 1 current', 'A', 'float', '-11', '11'),
    ('azim-motor1-overtemp', 'Azimuth motor 1 indicates an overtemperature', '', 'boolean'),
    ('azim-motor2-current', 'Azimuth motor 2 current', 'A', 'float', '-11', '11'),
    ('azim-motor2-overtemp', 'Azimuth motor 2 indicates an overtemperature', '', 'boolean'),
    ('azim-overcurrent-error', 'True if the current drawn by the azimuth drive exceeds the configured overcurrent threshold', '', 'boolean'),
    ('azim-plc-ext-box-overtemp', 'Azimuth PLC extension box reports an overtemperature or not', '', 'boolean'),
    ('azim-prelimit-ccw-reached', 'Azimuth axis prelimit has been reached in the counterclockwise direction', '', 'boolean'),
    ('azim-prelimit-cw-reached', 'Azimuth axis prelimit has been reached in the clockwise direction', '', 'boolean'),
    ('azim-range-switch-failed', 'Azimuth range switch signal is not as expected at either the azimuth travel limits or in the non-ambiguous range', '', 'boolean'),
    ('azim-servo-failed', 'True if any azimuth axis failure occurs', '', 'boolean'),
    ('azim-soft-limit-ccw-reached', 'Azimuth axis software limit has been reached in the counterclockwise direction', '', 'boolean'),
    ('azim-soft-limit-cw-reached', 'Azimuth axis software limit has been reached in the clockwise direction', '', 'boolean'),
    ('azim-soft-prelimit-ccw-reached', 'Azimuth axis software prelimit has been reached in the counterclockwise direction', '', 'boolean'),
    ('azim-soft-prelimit-cw-reached', 'Azimuth axis software prelimit has been reached in the clockwise direction', '', 'boolean'),
    ('cabinet-breakers-all-ok', 'Not ok if at least one of the automatic breakers inside the drive cabinet has tripped', '', 'boolean'),
    ('cabinet-overtemp-all-ok', 'Not ok if one of the overtemperature sensors in the drive cabinet reports an alarm', '', 'boolean'),
    ('can-bus-failed', 'Failure detected on ACU and servo amplifiers CAN bus', '', 'boolean'),
    ('cb-dc-sdc-general-closed', 'General DC circuit breaker located in SDC open or closed', '', 'boolean'),
    ('cb-pdc-he-compressor-closed', 'Helium Compressor circuit breaker (CB17) in PDC open or closed', '', 'boolean'),
    ('cb-pdc-ler-ingest-fan-closed', 'LER Ingest Fan circuit breaker (CB14) in PDC open or closed', '', 'boolean'),
    ('cb-pdc-power-ridb-closed', 'RIDB power supply circuit breaker (CB2) in PDC open or closed', '', 'boolean'),
    ('cb-ridb-digitiser1-closed', 'Digitiser1 circuit breaker (CB8) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-digitiser2-closed', 'Digitiser2 circuit breaker (CB9) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-digitiser3-closed', 'Digitiser3 circuit breaker (CB10) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-digitiser4-closed', 'Digitiser4 circuit breaker (CB11) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-receiver1-closed', 'Receiver1 circuit breaker (CB4) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-receiver2-closed', 'Receiver2 circuit breaker (CB5) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-receiver3-closed', 'Receiver3 circuit breaker (CB6) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-receiver4-closed', 'Receiver4 circuit breaker (CB7) in RIDB open or closed', '', 'boolean'),
    ('cb-ridb-vacuum-pump-closed', 'Vacuum pump circuit breaker (CB12) in RIDB open or closed', '', 'boolean'),
    ('cb-sdc-brake-power-closed', 'Brake Power Supply circuit breaker (CB27) in SDC open or closed', '', 'boolean'),
    ('cb-sdc-fans-closed', 'SDC Fans circuit breaker (CB21) in SDC open or closed', '', 'boolean'),
    ('cb-sdc-recv-controller-closed', 'Receiver Controller circuit breaker (CB23) in SDC open or closed', '', 'boolean'),
    ('cb-sdc-servo-amp-power-closed', 'Servo Amplifier Power Supply circuit breaker (CB26) in SDC open or closed', '', 'boolean'),
    ('control', 'Current control mode of the AP', '', 'discrete', 'remote', 'safe1', 'safe2', 'manual', 'local'),
    ('device-status', 'Summary of the Antenna Positioner operational status', '', 'discrete', 'ok', 'degraded', 'fail'),
    ('drive-power-supply-failed', 'The power supply module for the servo amplifiers failed or indicate an overtemperature', '', 'boolean'),
    ('e-stop-reason', 'Reason for the occurrence of an emergency stop', '', 'discrete',
            'azel-drives', 'none', 'ri-drives', 'pcu', 'outside-pedestal', 'ler', 'local', 'az-cable-wrap'),
    ('elev-amp-failed', 'Elevation amplifier or the regeneration resistor reports a problem', '', 'boolean'),
    ('elev-brake-failed', 'Elevation brake release problem occured', '', 'boolean'),
    ('elev-brakes-released', 'True if all elevation axis brakes are released', '', 'boolean'),
    ('elev-emergency-limit-down-reached', 'Elevation axis emergency-limit has been reached in the downwards direction', '', 'boolean'),
    ('elev-emergency-limit-up-reached', 'Elevation axis emergency-limit has been reached in the upwards direction', '', 'boolean'),
    ('elev-emergency2-limit-down-reached', 'Elevation axis emergency2-limit has been reached in the downwards direction', '', 'boolean'),
    ('elev-emergency2-limit-up-reached', 'Elevation axis emergency2-limit has been reached in the upwards direction', '', 'boolean'),
    ('elev-enc-failed', 'Elevation encoder has failed', '', 'boolean'),
    ('elev-hard-limit-down-reached', 'Elevation axis hard-limit has been reached in the downwards direction', '', 'boolean'),
    ('elev-hard-limit-up-reached', 'Elevation axis hard-limit has been reached in the upwards direction', '', 'boolean'),
    ('elev-motion-error', 'Elevation axis does not move although commanded to do so', '', 'boolean'),
    ('elev-motor-current', 'Elevation motor current', 'A', 'float', '-11', '11'),
    ('elev-motor-overtemp', 'Elevation motor indicates an overtemperature', '', 'boolean'),
    ('elev-overcurrent-error', 'True if the current drawn by the elevation drive exceeds the configured overcurrent threshold', '', 'boolean'),
    ('elev-prelimit-down-reached', 'Elevation axis prelimit has been reached in the downwards direction', '', 'boolean'),
    ('elev-prelimit-up-reached', 'Elevation axis prelimit has been reached in the upwards direction', '', 'boolean'),
    ('elev-servo-failed', 'True if any elevation axis failure occurs', '', 'boolean'),
    ('elev-soft-limit-down-reached', 'Elevation axis software limit has been reached in the downwards direction', '', 'boolean'),
    ('elev-soft-limit-up-reached', 'Elevation axis software limit has been reached in the upwards direction', '', 'boolean'),
    ('elev-soft-prelimit-down-reached', 'Elevation axis software prelimit has been reached in the downwards direction', '', 'boolean'),
    ('elev-soft-prelimit-up-reached', 'Elevation axis software prelimit has been reached in the upwards direction', '', 'boolean'),
    ('failure-present', 'Indicates whether at least one failure that prevents antenna movement is currently latched', '', 'boolean'),
    ('hatch-door-open', 'Hatch door open or not', '', 'boolean'),
    ('indexer-position', 'The current receiver indexer position as a discrete mapped to the receiver band it is at', '', 'discrete', 'undefined', 'l', 's', 'moving', 'x', 'u'),
    ('indexer-position-raw', 'The current receiver indexer position as reported in its native format', 'deg', 'float', '0', '120'),
    ('key-switch-emergency-limit-bypass-enabled', 'Key switch for emergency limit override functionality is enabled or not', '', 'boolean'),
    ('key-switch-safe1-enabled', 'Key switch for SAFE function in the SAFE 1 position or not', '', 'boolean'),
    ('key-switch-safe2-enabled', 'Key switch for SAFE function in the SAFE 2 position or not', '', 'boolean'),
    ('local-time-synced', 'Local time synced or not', '', 'boolean'),
    ('lubrication-azim-bearing-ok', 'Lubrication at the azimuth bearing ok or not', '', 'boolean'),
    ('lubrication-azim-gearbox-ok', 'Lubrication at the azimuth gearbox ok or not', '', 'boolean'),
    ('lubrication-elev-bearing-ok', 'Lubrication at the elevation bearing ok or not', '', 'boolean'),
    ('lubrication-elev-jack-ok', 'Lubrication at the elevation jack ok or not', '', 'boolean'),
    ('mode', 'Current operational mode of the AP', '', 'discrete', 'stowing', 'star-track', 'track', 'stop', 'maintenance', 'going-to-maintenance', 'rate', 'shutdown', 'e-stop', 'stowed', 'slew'),
    ('motion-profiler-azim-enabled', 'ACU motion profiler for azimuth axis enabled or disabled', '', 'boolean'),
    ('motion-profiler-elev-enabled', 'ACU motion profiler for elevation axis enabled or disabled', '', 'boolean'),
    ('on-source-threshold', "Current threshold value used by the 'on-source-threshold' condition to determine if on target", 'deg', 'float', '-10000000', '10000000'),
    ('on-target', 'AP is on target', '', 'boolean'),
    ('ped-door-open', 'Pedestal door open or not', '', 'boolean'),
    ('point-error-refraction-enabled', 'RF refraction pointing error correction enabled or disabled', '', 'boolean'),
    ('point-error-systematic-enabled', 'Systematic pointing error correction enabled or disabled', '', 'boolean'),
    ('point-error-tiltmeter-enabled', 'Tiltmeter pointing error correction enabled or disabled', '', 'boolean'),
    ('power-24-volt-ok', 'Internal 24V power ok (available) or not (missing)', '', 'boolean'),
    ('profibus-error', 'Profibus cable interrupted or stations not responding', '', 'boolean'),
    ('reboot-reason', 'Reports reason for last reboot of the ACU', '', 'discrete', 'powerfailure', 'remote', 'plc-watchdog', 'other'),
    ('refr-corr-elev', 'Currently applied refraction correction in elevation ', 'arcsec', 'float', '-300', '300'),
    ('regen-resistor-overtemp', 'The regeneration resistor of the power supply module for the servo amplifiers reports an overtemperature or not', '', 'boolean'),
    ('requested-azim', 'Target azimuth position', 'deg', 'float', '-185', '275'),
    ('requested-azim-rate', 'Requested azimuth velocity', 'deg/s', 'float', '-2', '2'),
    ('requested-elev', 'Target elevation position', 'deg', 'float', '15', '92'),
    ('requested-elev-rate', 'Requested elevation velocity', 'deg/s', 'float', '-1', '1'),
    ('ridx-amp-failed', 'Receiver indexer amplifier or the regeneration resistor reports a problem', '', 'boolean'),
    ('ridx-brake-failed', 'Receiver indexer brake release problem occured', '', 'boolean'),
    ('ridx-brakes-released', 'True if all receiver indexer axis brakes are released', '', 'boolean'),
    ('ridx-enc-failed', 'Receiver indexer encoder has failed', '', 'boolean'),
    ('ridx-hard-limit-ccw-reached', 'Receiver indexer hard-limit has been reached in the counterclockwise direction', '', 'boolean'),
    ('ridx-hard-limit-cw-reached', 'Receiver indexer hard-limit has been reached in the clockwise direction', '', 'boolean'),
    ('ridx-motion-error', 'Receiver indexer axis does not move although commanded to do so', '', 'boolean'),
    ('ridx-motor-current', 'Receiver indexer motor current', 'A', 'float', '-2.5', '2.5'),
    ('ridx-motor-overtemp', 'Receiver indexer motor indicates an overtemperature', '', 'boolean'),
    ('ridx-overcurrent-error', 'True if the current drawn by the receiver indexer drive exceeds the configured overcurrent threshold', '', 'boolean'),
    ('ridx-servo-failed', 'True if any receiver indexer axis failure occurs', '', 'boolean'),
    ('ridx-soft-limit-ccw-reached', 'Receiver indexer software limit has been reached in the counterclockwise direction', '', 'boolean'),
    ('ridx-soft-limit-cw-reached', 'Receiver indexer software limit has been reached in the clockwise direction', '', 'boolean'),
    ('ridx-soft-prelimit-ccw-reached', 'Receiver indexer software prelimit has been reached in the counterclockwise direction', '', 'boolean'),
    ('ridx-soft-prelimit-cw-reached', 'Receiver indexer software prelimit has been reached in the clockwise direction', '', 'boolean'),
    ('sdc-drive-power-on', 'Drive power supply contactor in SDC on or off', '', 'boolean'),
    ('sdc-power-ok', 'Power supply of the SDC ok or not (includes detection of a missing phase)', '', 'boolean'),
    ('sp-pdc-surge-detected', 'Surge protection device in PDC detected an electrical surge or not', '', 'boolean'),
    ('spem-corr-azim', 'Currently applied pointing error correction in azimuth based on systematic error model', 'arcsec', 'float', '-3600', '3600'),
    ('spem-corr-elev', 'Currently applied pointing error correction in elevation based on systematic error model', 'arcsec', 'float', '-3600', '3600'),
    ('stow-time-period', 'Time period for stow after communication is lost', 'sec', 'integer', '60', '3600'),
    ('struct-tilt-temp', 'Temperature as reported by the tiltmeter', 'degC', 'float', '-5', '40'),
    ('struct-tilt-x', 'Structural tilt in X direction', 'arcsec', 'float', '-120', '120'),
    ('struct-tilt-y', 'Structural tilt in Y direction', 'arcsec', 'float', '-120', '120'),
    ('temperature-sensor1', 'The value from the first temperature sensor installed in the antenna tower of AP#1 only.', 'degC', 'float', '-5', '45'),
    ('temperature-sensor2', 'The value from the second temperature sensor installed in the antenna tower of AP#1 only.', 'degC', 'float', '-5', '45'),
    ('temperature-sensor3', 'The value from the third temperature sensor installed in the antenna tower of AP#1 only.', 'degC', 'float', '-5', '45'),
    ('temperature-sensor4', 'The value from the fourth temperature sensor installed in the antenna tower of AP#1 only.', 'degC', 'float', '-5', '45'),
    ('tilt-corr-azim', 'Currently applied pointing error correction in azimuth based on tiltmeter readout', 'arcsec', 'float', '-3600', '3600'),
    ('tilt-corr-elev', 'Currently applied pointing error correction in elevation based on tiltmeter readout', 'arcsec', 'float', '-3600', '3600'),
    ('tilt-param-an0', 'Currently applied parameter AN0 for average tilt of tower towards North.', 'arcsec', 'float', '-3600', '3600'),
    ('tilt-param-aw0', 'Currently applied parameter AW0 for average tilt of tower towards West.', 'arcsec', 'float', '-3600', '3600'),
    ('tiltmeter-read-error', 'Reading from the tiltmeter failed', '', 'boolean'),
    ('track-stack-size', 'Number of track samples in the ACU sample stack', '', 'integer', '0', '3000'),
    ('warning-horn-enabled', 'Warning horn enabled or disabled', '', 'boolean'),
    ('warning-horn-sounding', 'Indicate if the warning horn is audibly sounding at this moment', '', 'boolean'),
    ('yoke-door-open', 'Yoke door open or not', '', 'boolean'),
    ('yoke-plc-ext-box-overtemp', 'Yoke PLC extension box reports an overtemperature or not', '', 'boolean'),
    ('sdc-unexpected-drive-power', 'TBD', '', 'boolean'),
    ('State', '', '', '', ''),
    ('Status', '', '', '', '')
]

EXPECTED_REQUEST_LIST =  [
    ('clear-track-stack'),
    ('enable-motion-profiler'),
    ('enable-point-error-refraction'),
    ('enable-point-error-systematic'),
    ('enable-point-error-tiltmeter'),
    ('enable-warning-horn'),
    ('halt'),
    ('help'),
    ('log-level'),
    ('maintenance'),
    ('rate'),
    ('reset-failures'),
    ('restart'),
    ('set-average-tilt-an0'),
    ('set-average-tilt-aw0'),
    ('sensor-list'),
    ('sensor-sampling'),
    ('sensor-value'),
    ('set-indexer-position'),
    ('set-on-source-threshold'),
    ('set-stow-time-period'),
    ('set-weather-data'),
    ('slew'),
    ('star-track'),
    ('stop'),
    ('stow'),
    ('track'),
    ('track-az-el'),
    ('version-list'),
    ('watchdog'),
    ('init'),
    ('state'),
    ('status'),
    ('turnoff'),
    ('turnon'),
]

class TestProxyWrapper(object):
    def __init__(self, test_instance, device_proxy):
        self.device_proxy = device_proxy
        self.test_inst = test_instance
        
    def assertCommandSucceeds(self, command_name, *params, **kwargs):
        """Assert that given command succeeds when called with given parameters.

        Optionally also checks the arguments.

        Parameters
        ----------
        requestname : str
            The name of the request.
        params : list of objects
            The parameters with which to call the request.
        """
        print params
        
        if params == ():
            reply = self.device_proxy.command_inout(command_name)
        else:
            reply = self.device_proxy.command_inout(command_name, params)
            
        reply_name = self.device_proxy.command_query(command_name).cmd_name

        self.test_inst.assertEqual(reply_name, command_name, "Reply to request '%s'"
                              "has name '%s'." % (command_name, reply_name))


        print reply
        print type(reply)
        msg = ("Expected request '%s' called with parameters %r to succeed, "
               "but it failed %s."
               % (command_name, params, ("with error '%s'" % reply[1]
                                         if len(reply) >= 2 else
                                         "(with no error message)")))
                                         
        self.test_inst.assertTrue(reply[0]=='ok', msg)
        
    
    def assertCommandFails(self, command_name, *params, **kwargs):
        """Assert that given command fails when called with given parameters.

        Parameters
        ----------
        requestname : str
            The name of the request.
        params : list of objects
            The parameters with which to call the request.
        """                                                    *params))
        if params == ():
            reply = self.device_proxy.command_inout(command_name)
        else:
            reply = self.device_proxy.command_inout(command_name, params)
            
        reply_name = self.device_proxy.command_query(command_name).cmd_name
        
        print reply
        msg = "Reply to command '%s' has name '%s'." % (command_name, reply_name)
        self.test_inst.assertEqual(reply_name, command_name, msg)

        msg = ("Expected request '%s' called with parameters %r to fail, "
               "but it was successful." % (command_name, params))
        self.test_inst.assertFalse(reply[0]=='ok', msg)

    def test_sensor_list(self, expected_attributes, ignore_descriptions=False):
        """Test that list of attributes on the device equals the provided list.

        Parameters
        ----------
        expected_attributes : list of tuples
            The list of expected sensors. Each tuple contains the arguments
            returned by each sensor-list inform, as unescaped strings.
        ignore_descriptions : boolean, optional
            If this is true, sensor descriptions will be ignored in the
            comparison.

        """
        def sensortuple(name, description, units, stype, *params):
            # ensure float params reduced to the same format
            if stype == "float":
                params = ["%g" % float(p) for p in params]
            return (name, description, units, stype) + tuple(params)

        #reply, informs = self.blocking_request(Message.request("sensor-list"))
#        attr = self.get_attribute_list()
#
#        msg = ("Could not retrieve sensor list: %s"
#               % (reply.arguments[1] if len(reply.arguments) >= 2 else ""))
#        self.test.assertTrue(reply.reply_ok(), msg)
#
#        expected_sensors = [sensortuple(*t) for t in expected_sensors]
#        got_sensors = [sensortuple(*m.arguments) for m in informs]

        # print ",\n".join([str(t) for t in got_sensors])

#        if ignore_descriptions:
#            expected_sensors = [s[:1] + s[2:] for s in expected_sensors]
#            got_sensors = [s[:1] + s[2:] for s in got_sensors]
#
#        expected_set = set(expected_sensors)
#        got_set = set(got_sensors)
#
#        msg = ("Sensor list differs from expected list.\n"
#               "These sensors are missing:\n%s\n"
#               "Found these unexpected sensors:\n%s"
#               % ("\n".join(sorted([str(t) for t in expected_set - got_set])),
#                  "\n".join(sorted([str(t) for t in got_set - expected_set]))))
#        self.test.assertEqual(got_set, expected_set, msg)
        
        
class MkatApKatcpTests(DeviceTestCase):
    """
    KATCP tests that can be run on both the AP Simulator and the ACU HW
    Simulator.
    """
    addr = None
    sensor_lag = 0.2
    external = False
    EXPECTED_VERSION_CONNECT_INFORMS = [
        '#version-connect katcp-protocol*',
        '#version-connect katcp-library*',
        '#version-connect katcp-device*',
    ]

    device = MkatAntennaPositioner
    
    def formatter(self, sensor_name):
        """
        Removes the dash(es) in the sensor name and replaces them with underscore(s)
        to guard against illegal attribute identifiers in TANGO
        
        Parameters
        ----------
        sensor_name : str
            The name of the sensor. For example:
            
            'actual-azim'
        
        Returns
        -------
        attr_name : str
            The legal identifier for an attribute. For example:
            
            'actual_azim'
        """
        attr_name = sensor_name.replace('-', '_')
        return attr_name

    def unformatter(self, attr_name):
        """
        Removes the underscore(s) in the attribute name and replaces them with 
        dashe(s), so that we can access the the KATCP Sensors using their identifiers
        
        Parameters
        ----------
        attr_name : str
            The name of the sensor. For example:
            
            'actual_azim'
        
        Returns
        -------
        sensor_name : str
            The legal identifier for an attribute. For example:
            
            'actual-azim'
        """
        sensor_name = attr_name.replace('_', '-')
        return sensor_name

    def test_sensor_list(self):
        def log_expected_sensor_list():
            """Useful debug function to generate EXPECTED_SENSOR_LIST"""
            #reply, informs = self.client.blocking_request(Message.request("sensor-list"))
            #for inform in informs:
                #logger.debug("(%s)," % ', '.join(["'%s'" % str(i) for i in inform.arguments]))
              #  logger.debug(str(inform))
            pass

        #log_expected_sensor_list() # Useful to get the expected list

        #self.client.test_sensor_list(EXPECTED_SENSOR_LIST, ignore_descriptions=True)

    def test_sensor_list_basic(self):
        """
        Test sensor list but only check the sensor names.
        """
        def get_actual_sensor_list():
            """Return the list of actual sensors of the connected server"""
            #reply, informs = self.client.blocking_request(
             #       Message.request("sensor-list"))
            attr_list = self.device.get_attribute_list()
            sens_list = [self.unformatter(attr) for attr in attr_list]
            return sens_list

        if self.external:
            # Some sensors are specific to the simulator and not specified in the
            # ICD and as such should not be tested for on the KATCP interface
            # of external devices.
           # expected_set = set([s[0]
               # for s in EXPECTED_SENSOR_LIST
                #if s[0] not in ['actual-azim-rate', 'actual-elev-rate',
                               # 'requested-azim-rate', 'requested-elev-rate']
            #])
            pass
        else:
            expected_set = set([s[0] for s in EXPECTED_SENSOR_LIST])
        actual_set = set(get_actual_sensor_list())

        self.assertEqual(actual_set, expected_set,
            "\n\n!Actual sensor list differs from expected list!\n\nThese sensors are"
            " missing:\n%s\n\nFound these unexpected sensors:\n%s"
            % ("\n".join(sorted([str(t) for t in expected_set - actual_set])),
               "\n".join(sorted([str(t) for t in actual_set - expected_set]))))

    def test_request_list(self):
        def log_expected_request_list():
            """Useful debug function to generate EXPECTED_REQUEST_LIST"""
            #reply, informs = self.client.blocking_request(Message.request("help"))
            #for inform in informs:
              #  logger.debug("('%s')," % inform.arguments[0])
            pass

        def get_actual_request_list():
            """Return the list of actual requests of the connected server"""
            #reply, informs = self.client.blocking_request(Message.request("help"))
            command_list = self.device.command_list_query()
            req_list = [self.unformatter(command.cmd_name.lower()) for command in command_list]
            return req_list

        #log_expected_sensor_list() # Useful to get the expected list

        expected_set = set(EXPECTED_REQUEST_LIST)
        actual_set = set(get_actual_request_list())
        self.assertEqual(actual_set, expected_set,
            "\n\n!Actual request list differs from expected list!\n\nThese requests are"
            " missing:\n%s\n\nFound these unexpected requests:\n%s"
            % ("\n".join(sorted([str(t) for t in expected_set - actual_set])),
               "\n".join(sorted([str(t) for t in actual_set - expected_set]))))


class TestMkatAp(DeviceTestCase):

    external = False
    device = MkatAntennaPositioner
    
    def setUp(self):
        #self.addCleanup(self.tear_down_threads)
        #self.set_up_device_and_client(MkatApDevice, MkatApModel, MkatApTestDevice)
        super(TestMkatAp, self).setUp()
        self.instance = MkatAntennaPositioner.instances[self.device.name()]
        self.client = TestProxyWrapper(self, self.device)
#        if not self.external:
#            # MkatApModel with faster azim and elev max rates to allow tests to execute
#            # quicker.
#            self.client.assertCommandSucceeds("set_max_rate_azim_drive", 20.0)
#            self.client.assertCommandSucceeds("set-max-rate-elev-drive", 10.0)
         
        def cleanup_refs(): del self.instance
        self.addCleanup(cleanup_refs)
        
    def test_rate(self):
        AZ_REQ_RATE = 1.9
        EL_REQ_RATE = 0.9
        self.client.assertCommandFails("Rate", AZ_REQ_RATE, EL_REQ_RATE)
        self.client.assertCommandSucceeds("TurnOn")
        self.client.assertCommandSucceeds("Stop")
        self.client.assertCommandSucceeds("Rate", AZ_REQ_RATE, EL_REQ_RATE)
        self.assertEqual(self.device.mode, "rate")
        az_req_rate = self.device.requested_azim_rate
        el_req_rate = self.device.requested_elev_rate
        self.assertEqual(az_req_rate, AZ_REQ_RATE)
        self.assertEqual(el_req_rate, EL_REQ_RATE)
        az_rate = self.device.actual_azim_rate
        el_rate = self.device.actual_elev_rate
        self.assertEqual(az_rate, AZ_REQ_RATE)
        self.assertEqual(el_rate, EL_REQ_RATE)
        print ("azim-rate req=%.2f actual=%.2f" % (az_req_rate, az_rate))
        print ("elev-rate req=%.2f actual=%.2f" % (el_req_rate, el_rate))
        az_pos1 = self.device.actual_azim
        el_pos1 = self.device.actual_elev
        time.sleep(1)
        az_pos2 = self.device.actual_azim
        el_pos2 = self.device.actual_elev
        self.assertTrue(az_pos2 > az_pos1)
        self.assertTrue(el_pos2 > el_pos1)
        az_rate = self.device.actual_azim_rate
        el_rate = self.device.actual_elev_rate
        print ("azim-rate req=%.2f actual=%.2f" % (az_req_rate, az_rate))
        print ("elev-rate req=%.2f actual=%.2f" % (el_req_rate, el_rate))
        self.client.assertCommandSucceeds("Stop")
        self.assertEqual(self.device.mode, "stop")
        az_pos1 = self.device.actual_azim
        el_pos1 = self.device.actual_elev
        time.sleep(1)
        az_pos2 = self.device.actual_azim
        el_pos2 = self.device.actual_elev
        self.assertTrue(az_pos2 == az_pos1)
        self.assertTrue(el_pos2 == el_pos1)
        
        
    def test_slew(self):
        AZ_REQ_POS = -140
        EL_REQ_POS = 30
        self.client.assertCommandSucceeds("TurnOn")
        self.client.assertCommandFails("Slew", AZ_REQ_POS, EL_REQ_POS)
        self.client.assertCommandSucceeds("Stop")
        self.client.assertCommandSucceeds("Slew", AZ_REQ_POS, EL_REQ_POS)
        self.assertEqual(self.device.mode, "slew")
        az_req_pos = self.device.requested_azim
        el_req_pos = self.device.requested_elev
        self.assertEqual(az_req_pos, AZ_REQ_POS)
        self.assertEqual(el_req_pos, EL_REQ_POS)
#        self.client.wait_until_sensor_equals(2, 'on-target', 0, sensortype=bool)
#        self.client.wait_until_sensor_equals(10, 'on-target', 1, sensortype=bool)
#        azim = self.device.actual_azim
#        elev = self.device.actual_elev
#        self.assertAlmostEqual(az_req_pos, azim, 2)
#        self.assertAlmostEqual(el_req_pos, elev, 2)
#        self.client.assert_request_succeeds("stop")
#        self.assertEqual(self.client.get_sensor_value("mode"), "stop")
##
#    def test_switch_between_track_and_slew(self):
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(1, 'mode', 'stop')
#        self.client.assert_request_succeeds("track")
#        self.client.wait_until_sensor_equals(1, 'mode', 'track')
#        self.client.assert_request_succeeds("slew", 210, 65)
#        self.client.wait_until_sensor_equals(1, 'mode', 'slew')
#        self.client.assert_request_succeeds("slew", 220, 75)
#        self.client.wait_until_sensor_equals(1, 'mode', 'slew')
#        self.client.assert_request_succeeds("track")
#        self.client.wait_until_sensor_equals(1, 'mode', 'track')
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(1, 'mode', 'stop')
#
#    def test_track(self):
#        MAX_AZIM_FOR_TEST = 250
#        MAX_ELEV_FOR_TEST = 70
#        MAX_TRACK_WAIT_TIME = 40 # 5s + 50samples*0.5s/sample = 30
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stop')
#        azim = round(self.client.get_sensor_value("actual-azim", float), 3)
#        elev = round(self.client.get_sensor_value("actual-elev", float), 3)
#        if azim > MAX_AZIM_FOR_TEST:
#            azim = MAX_AZIM_FOR_TEST
#        if elev > MAX_ELEV_FOR_TEST:
#            elev = MAX_ELEV_FOR_TEST
#        # Load a few samples to track
#        t0 = time.time() + 5
#        for i in xrange(0, 50):
#            # New sample every 500ms with 0.1deg movement
#            self.client.assert_request_succeeds("track-az-el",
#                    t0+(i*0.5),
#                    (azim+5)+(i*0.1),
#                    (elev+5)+(i*0.1))
#        # Start tracking
#        self.client.assert_request_succeeds("track")
#        self.client.wait_until_sensor_equals(2, 'mode', 'track')
#        self.client.wait_until_sensor_equals(2, 'on-target', 0, sensortype=bool)
#        self.client.wait_until_sensor_equals(MAX_TRACK_WAIT_TIME,
#            'on-target', 1, sensortype=bool)
#        # Check requested vs actual after target reached
#        az_req_pos = round(self.client.get_sensor_value("requested-azim", float), 3)
#        el_req_pos = round(self.client.get_sensor_value("requested-elev", float), 3)
#        azim = round(self.client.get_sensor_value("actual-azim", float), 3)
#        elev = round(self.client.get_sensor_value("actual-elev", float), 3)
#        self.assertAlmostEqual(az_req_pos, azim, 2)
#        self.assertAlmostEqual(el_req_pos, elev, 2)
#        # Mode should still be track
#        self.client.wait_until_sensor_equals(2, 'mode', 'track')
#        # Add a few samples in the past (these should be ignored)
#        t1 = time.time() - 200
#        self.client.assert_request_succeeds("track-az-el", t1, azim+2, elev+2)
#        self.client.assert_request_succeeds("track-az-el", t1+0.5, azim+2.5, elev+2.5)
#        self.client.assert_request_succeeds("track-az-el", t1+1, azim+3, elev+3)
#        self.client.assert_request_succeeds("track-az-el", t1+1.5, azim+3.5, elev+3.5)
#        self.client.wait_until_sensor_equals(2, 'on-target', 1, sensortype=bool)
#        self.assertAlmostEqual(az_req_pos, azim, 2)
#        self.assertAlmostEqual(el_req_pos, elev, 2)
#        # Add a few more samples, and check that tracking continues
#        t2 = time.time() + 2
#        self.client.assert_request_succeeds("track-az-el", t2, azim+2, elev+2)
#        self.client.assert_request_succeeds("track-az-el", t2+0.5, azim+2.5, elev+2.5)
#        self.client.assert_request_succeeds("track-az-el", t2+1, azim+3, elev+3)
#        self.client.assert_request_succeeds("track-az-el", t2+1.5, azim+3.5, elev+3.5)
#        self.client.wait_until_sensor_equals(2, 'on-target', 0, sensortype=bool)
#        # Stop the drive
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stop')
#
#    def test_stow(self):
#        # Make test start nice and close to the actual stow position
#        ELEV_FOR_TEST = MkatApModel.STOW_ELEV - 2
#        MAX_STOW_WAIT_TIME = 5
#        self.testclient.assert_request_succeeds("set-elev-drive-position",
#            ELEV_FOR_TEST)
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stop')
#        self.client.assert_request_succeeds("stow")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stowing')
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stop')
#        self.client.assert_request_succeeds("stow")
#        self.client.wait_until_sensor_equals(MAX_STOW_WAIT_TIME, 'mode', 'stowed')
#
#    def test_maintenance(self):
#        # Make test start nice and close to the actual maint position
#        AZIM_FOR_TEST = MkatApModel.MAINT_AZIM - 5
#        ELEV_FOR_TEST = MkatApModel.MAINT_ELEV - 2
#        MAX_MAINT_WAIT_TIME = 5
#        self.testclient.assert_request_succeeds("set-azim-drive-position",
#            AZIM_FOR_TEST)
#        self.testclient.assert_request_succeeds("set-elev-drive-position",
#            ELEV_FOR_TEST)
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stop')
#        self.client.assert_request_succeeds("maintenance")
#        self.client.wait_until_sensor_equals(2, 'mode', 'going-to-maintenance')
#        self.client.assert_request_succeeds("stop")
#        self.client.wait_until_sensor_equals(2, 'mode', 'stop')
#        self.client.assert_request_succeeds("maintenance")
#        self.client.wait_until_sensor_equals(MAX_MAINT_WAIT_TIME, 'mode',
#            'maintenance')
#
#    def test_set_indexer_position(self):
#        # Test for 'l'
#        self.client.assert_request_succeeds("set-indexer-position", "l")
#        while self.client.get_sensor_value("indexer-position") == "moving":
#            print ("ridx-pos=%.4f" %
#                self.client.get_sensor_value("indexer-position-raw", float))
#            time.sleep(0.5)
#        self.assertEqual(self.client.get_sensor_value("indexer-position"), "l")
#        self.assertAlmostEqual(self.client.get_sensor_value("indexer-position-raw", float),
#                4.0, 2)
#        # Test for 'u'
#        self.client.assert_request_succeeds("set-indexer-position", "u")
#        while self.client.get_sensor_value("indexer-position") == "moving":
#            print ("ridx-pos=%.4f" %
#                self.client.get_sensor_value("indexer-position-raw", float))
#            time.sleep(0.5)
#        self.assertEqual(self.client.get_sensor_value("indexer-position"), "u")
#        self.assertAlmostEqual(self.client.get_sensor_value("indexer-position-raw", float),
#                6.0, 2)
#        # Test for 'x'
#        self.client.assert_request_succeeds("set-indexer-position", "x")
#        while self.client.get_sensor_value("indexer-position") == "moving":
#            print ("ridx-pos=%.4f" %
#                self.client.get_sensor_value("indexer-position-raw", float))
#            time.sleep(0.5)
#        self.assertEqual(self.client.get_sensor_value("indexer-position"), "x")
#        self.assertAlmostEqual(self.client.get_sensor_value("indexer-position-raw", float),
#                2.0, 2)
#        # Test for 's'
#        self.client.assert_request_succeeds("set-indexer-position", "s")
#        while self.client.get_sensor_value("indexer-position") == "moving":
#            print ("ridx-pos=%.4f" %
#                self.client.get_sensor_value("indexer-position-raw", float))
#            time.sleep(0.5)
#        self.assertEqual(self.client.get_sensor_value("indexer-position"), "s")
#        self.assertAlmostEqual(self.client.get_sensor_value("indexer-position-raw", float),
#                8.0, 2)
#        # Test some invalid ridx positions
#        self.client.assert_request_fails("set-indexer-position", "k")
#        self.assertEqual(self.client.get_sensor_value("indexer-position"), "s")
#        self.client.assert_request_fails("set-indexer-position", "moving")
#        self.assertEqual(self.client.get_sensor_value("indexer-position"), "s")
#
#    def test_set_on_source_threshold(self):
#        self.client.assert_request_succeeds("stop")
#        # Slew to a position and check that threshold is the default 1e-6
#        AZ_REQ_POS = -170
#        EL_REQ_POS = 20
#        self.client.assert_request_succeeds("slew", AZ_REQ_POS, EL_REQ_POS)
#        self.client.wait_until_sensor_equals(2, 'on-target', 0, sensortype=bool)
#        self.client.wait_until_sensor_equals(30, 'on-target', 1, sensortype=bool)
#        self.assertAlmostEqual(self.client.get_sensor_value("actual-azim", float),
#                AZ_REQ_POS, 2)
#        self.assertAlmostEqual(self.client.get_sensor_value("actual-elev", float),
#                EL_REQ_POS, 2)
#        self.client.assert_request_succeeds("stop")
#        # Set new threshold and slew to a position and check that the new threshold has
#        # been applied
#        self.client.assert_request_succeeds("set-on-source-threshold", 1e-1)
#        self.assertEqual(self.client.get_sensor_value("on-source-threshold", float),
#                1e-1)
#        AZ_REQ_POS = -160
#        EL_REQ_POS = 30
#        self.client.assert_request_succeeds("slew", AZ_REQ_POS, EL_REQ_POS)
#        self.client.wait_until_sensor_equals(2, 'on-target', 0, sensortype=bool)
#        self.client.wait_until_sensor_equals(30, 'on-target', 1, sensortype=bool)
#        self.assertAlmostEqual(self.client.get_sensor_value("actual-azim", float),
#                AZ_REQ_POS, 0)
#        self.assertAlmostEqual(self.client.get_sensor_value("actual-elev", float),
#                EL_REQ_POS, 0)
#        self.assertNotAlmostEqual(self.client.get_sensor_value("actual-azim", float),
#                AZ_REQ_POS, 2)
#        self.assertNotAlmostEqual(self.client.get_sensor_value("actual-elev", float),
#                EL_REQ_POS, 2)
#
#    def test_sensor_sampling(self):
#        # test for specific issue re incorrect sensor name in sampling
#
#        # start the sensor sampling
#        self.client.assert_request_succeeds("sensor-sampling", "requested-elev", "period", "1.0", args_echo=True)
#        get_informs = self.client.message_recorder(whitelist=["sensor-status"])
#
#        # wait for a couple of sample periods so that there is likely to be a message
#        time.sleep(2.0)
#
#        # look for a sensor-status inform for this sensor
#        elev_informs = [m for m in get_informs() if "requested-elev" in m.arguments]
#        self.assertTrue(elev_informs, "Expected a sensor-status inform for sensor 'requested-elev' but did not receive one.")
#
#    def test_sensor_sampling_reconnect(self):
#        # test sensor sampling not propagating to a new client connection
#
#        # start the sensor sampling
#        self.client.assert_request_succeeds("sensor-sampling", "requested-elev", "period", "1.0", args_echo=True)
#        get_informs = self.client.message_recorder(whitelist=["sensor-status"])
#
#        # wait for a couple of sample periods so that there is likely to be a message
#        time.sleep(2.0)
#
#        # look for a sensor-status inform for this sensor
#        elev_informs = [m for m in get_informs() if "requested-elev" in m.arguments]
#        self.assertTrue(elev_informs, "Expected a sensor-status inform for sensor 'requested-elev' but did not receive one.")
#
#        # kill the client and make a new one
#        self.replace_client()
#        get_informs = self.client.message_recorder(whitelist=["sensor-status"])
#
#        logging.info('sensor_sampling_reconnect: client reconnected: %s' % str(self.client.is_connected()))
#
#        # wait for a couple of sample periods to allow any messages to arrive
#        time.sleep(2.0)
#
#        elev_informs = [m for m in get_informs() if "requested-elev" in m.arguments]
#        self.assertFalse(elev_informs, "Did not expect a sensor-status inform for sensor 'requested-elev' after reconnection, but received one.")
#
#    def test_sensor_values_match_types(self):
#        """Test that the values returned by ?sensor-values match the types in ?sensor-list."""
#        sensors = {}
#        sensors_seen = set()
#
#        # list sensors
#        reply, informs = self.client.blocking_request(Message.request("sensor-list"))
#        self.assertEqual(reply.arguments[0], "ok")
#        self.assertEqual(int(reply.arguments[1]), len(informs))
#        for msg in informs:
#            name, description, units, formatted_type = msg.arguments[:4]
#            formatted_params = msg.arguments[4:]
#            sensor_type = Sensor.parse_type(formatted_type)
#            params = Sensor.parse_params(sensor_type, formatted_params)
#            sensors[name] = Sensor(sensor_type, name, description, units, params)
#
#        # check sensor values
#        reply, informs = self.client.blocking_request(Message.request("sensor-value"))
#        self.assertEqual(reply.arguments[0], "ok")
#        self.assertEqual(int(reply.arguments[1]), len(informs))
#        for msg in informs:
#            raw_timestamp = msg.arguments[0]
#            sensor_count = int(msg.arguments[1])
#            self.assertEqual(sensor_count, 1)
#            name, raw_status, raw_value = msg.arguments[2:]
#
#            sensor = sensors[name]
#            sensors_seen.add(name)
#            try:
#                sensor.set_formatted(raw_timestamp, raw_status, raw_value)
#            except ValueError, e:
#                self.fail("Could not set value %r [status: %r; timestamp: %r] for sensor %r: %r" %
#                    (raw_value, raw_status, raw_timestamp, name, e))
#
#        # check that we got values for all of them
#        self.assertEqual(set(sensors.keys()), sensors_seen)
#        

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)
    unittest.main()

