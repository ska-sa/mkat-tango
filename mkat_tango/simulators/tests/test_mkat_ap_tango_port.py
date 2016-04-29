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



if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)
    unittest.main()

