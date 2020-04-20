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
from __future__ import absolute_import, division, print_function


from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import *
from builtins import object
import unittest2 as unittest
import time
import logging

from devicetest import DeviceTestCase

from mkat_tango.simulators.mkat_ap_tango import MkatAntennaPositioner
from mkat_tango.translators.utilities import tangoname2katcpname

from PyTango import CmdArgType, DevState, DevFailed

logger = logging.getLogger(__name__)

EXPECTED_SENSOR_LIST = [
    ("actual-azim",
     "Actual azimuth position",
     "deg",
     "float",
     "-185",
     "275"),
    ("actual-azim-rate",
     "Actual azimuth velocity",
     "deg/s",
     "float",
     "-2",
     "2"),
    ("actual-elev",
     "Actual elevation position",
     "deg",
     "float",
     "15",
     "92"),
    ("actual-elev-rate",
     "Actual elevation velocity",
     "deg/s",
     "float",
     "-1",
     "1"),
    ("acu-plc-interface-error",
     "ACU detected communication error between ACU and PLC",
     "",
     "boolean",
     ),
    ("acu-speed-limited",
     "Due to excessive power requirements, the maximum velocities have been reduced",
     "",
     "boolean",
     ),
    ("acu-spline-status",
     ("Status relating to the number of track samples that are currently available in "
      "the ACU stack (green=optimal)"),
     "",
     "discrete",
     "green",
     "yellow",
     "red",
     ),
    ("amp-power-cycle-interlocked",
     ("True if waiting time presently applies because there has been too many power"
      " cycles of the main contactor for one of the drives"),
     "",
     "boolean",
     ),
    ("azim-amp1-failed",
     "Azimuth amplifier 1 or the regeneration resistor reports a problem",
     "",
     "boolean",
     ),
    ("azim-amp2-failed",
     "Azimuth amplifier 2 or the regeneration resistor reports a problem",
     "",
     "boolean",
     ),
    ("azim-aux1-mode-selected",
     "Azimuth axis auxiliary1 mode activated or not (i.e. azimuth only driven by motor 1",
     "",
     "boolean",
     ),
    ("azim-aux2-mode-selected",
     "Azimuth axis auxiliary2 mode activated or not (i.e. azimuth only driven by motor 2",
     "",
     "boolean",
     ),
    ("azim-brake1-failed",
     "Azimuth brake 1 release problem occured",
     "",
     "boolean"),
    ("azim-brake2-failed",
     "Azimuth brake 2 release problem occured",
     "",
     "boolean"),
    ("azim-brakes-released",
     "True if all azimuth axis brakes are released",
     "",
     "boolean",
     ),
    ("azim-emergency-limit-ccw-reached",
     "Azimuth axis emergency-limit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("azim-emergency-limit-cw-reached",
     "Azimuth axis emergency-limit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("azim-emergency2-limit-ccw-reached",
     "Azimuth axis emergency2-limit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("azim-emergency2-limit-cw-reached",
     "Azimuth axis emergency2-limit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("azim-enc-failed",
     "Azimuth encoder has failed",
     "",
     "boolean"),
    ("azim-hard-limit-ccw-reached",
     "Azimuth axis hard-limit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("azim-hard-limit-cw-reached",
     "Azimuth axis hard-limit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("azim-motion-error",
     "Azimuth axis does not move although commanded to do so",
     "",
     "boolean",
     ),
    ("azim-motor1-current",
     "Azimuth motor 1 current",
     "A",
     "float",
     "-11",
     "11"),
    ("azim-motor1-overtemp",
     "Azimuth motor 1 indicates an overtemperature",
     "",
     "boolean",
     ),
    ("azim-motor2-current",
     "Azimuth motor 2 current",
     "A",
     "float",
     "-11",
     "11"),
    ("azim-motor2-overtemp",
     "Azimuth motor 2 indicates an overtemperature",
     "",
     "boolean",
     ),
    ("azim-overcurrent-error",
     ("True if the current drawn by the azimuth drive exceeds the"
      " configured overcurrent threshold"),
     "",
     "boolean",
     ),
    ("azim-plc-ext-box-overtemp",
     "Azimuth PLC extension box reports an overtemperature or not",
     "",
     "boolean",
     ),
    ("azim-prelimit-ccw-reached",
     "Azimuth axis prelimit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("azim-prelimit-cw-reached",
     "Azimuth axis prelimit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("azim-range-switch-failed",
     ("Azimuth range switch signal is not as expected at either the azimuth travel"
      " limits or in the non-ambiguous range"),
     "",
     "boolean",
     ),
    ("azim-servo-failed",
     "True if any azimuth axis failure occurs",
     "",
     "boolean"),
    ("azim-soft-limit-ccw-reached",
     "Azimuth axis software limit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("azim-soft-limit-cw-reached",
     "Azimuth axis software limit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("azim-soft-prelimit-ccw-reached",
     "Azimuth axis software prelimit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("azim-soft-prelimit-cw-reached",
     "Azimuth axis software prelimit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("cabinet-breakers-all-ok",
     ("Not ok if at least one of the automatic breakers"
      " inside the drive cabinet has tripped"),
     "",
     "boolean",
     ),
    ("cabinet-overtemp-all-ok",
     "Not ok if one of the overtemperature sensors in the drive cabinet reports an alarm",
     "",
     "boolean",
     ),
    ("can-bus-failed",
     "Failure detected on ACU and servo amplifiers CAN bus",
     "",
     "boolean",
     ),
    ("cb-dc-sdc-general-closed",
     "General DC circuit breaker located in SDC open or closed",
     "",
     "boolean",
     ),
    ("cb-pdc-he-compressor-closed",
     "Helium Compressor circuit breaker (CB17) in PDC open or closed",
     "",
     "boolean",
     ),
    ("cb-pdc-ler-ingest-fan-closed",
     "LER Ingest Fan circuit breaker (CB14) in PDC open or closed",
     "",
     "boolean",
     ),
    ("cb-pdc-power-ridb-closed",
     "RIDB power supply circuit breaker (CB2) in PDC open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-digitiser1-closed",
     "Digitiser1 circuit breaker (CB8) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-digitiser2-closed",
     "Digitiser2 circuit breaker (CB9) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-digitiser3-closed",
     "Digitiser3 circuit breaker (CB10) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-digitiser4-closed",
     "Digitiser4 circuit breaker (CB11) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-receiver1-closed",
     "Receiver1 circuit breaker (CB4) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-receiver2-closed",
     "Receiver2 circuit breaker (CB5) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-receiver3-closed",
     "Receiver3 circuit breaker (CB6) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-receiver4-closed",
     "Receiver4 circuit breaker (CB7) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-ridb-vacuum-pump-closed",
     "Vacuum pump circuit breaker (CB12) in RIDB open or closed",
     "",
     "boolean",
     ),
    ("cb-sdc-brake-power-closed",
     "Brake Power Supply circuit breaker (CB27) in SDC open or closed",
     "",
     "boolean",
     ),
    ("cb-sdc-fans-closed",
     "SDC Fans circuit breaker (CB21) in SDC open or closed",
     "",
     "boolean",
     ),
    ("cb-sdc-recv-controller-closed",
     "Receiver Controller circuit breaker (CB23) in SDC open or closed",
     "",
     "boolean",
     ),
    ("cb-sdc-servo-amp-power-closed",
     "Servo Amplifier Power Supply circuit breaker (CB26) in SDC open or closed",
     "",
     "boolean",
     ),
    ("control",
     "Current control mode of the AP",
     "",
     "discrete",
     "remote",
     "safe1",
     "safe2",
     "manual",
     "local",
     ),
    ("device-status",
     "Summary of the Antenna Positioner operational status",
     "",
     "discrete",
     "ok",
     "degraded",
     "fail",
     ),
    ("drive-power-supply-failed",
     ("The power supply module for the servo amplifiers"
      " failed or indicate an overtemperature"),
     "",
     "boolean",
     ),
    ("e-stop-reason",
     "Reason for the occurrence of an emergency stop",
     "",
     "discrete",
     "azel-drives",
     "none",
     "ri-drives",
     "pcu",
     "outside-pedestal",
     "ler",
     "local",
     "az-cable-wrap",
     ),
    ("elev-amp-failed",
     "Elevation amplifier or the regeneration resistor reports a problem",
     "",
     "boolean",
     ),
    ("elev-brake-failed",
     "Elevation brake release problem occured",
     "",
     "boolean"),
    ("elev-brakes-released",
     "True if all elevation axis brakes are released",
     "",
     "boolean",
     ),
    ("elev-emergency-limit-down-reached",
     "Elevation axis emergency-limit has been reached in the downwards direction",
     "",
     "boolean",
     ),
    ("elev-emergency-limit-up-reached",
     "Elevation axis emergency-limit has been reached in the upwards direction",
     "",
     "boolean",
     ),
    ("elev-emergency2-limit-down-reached",
     "Elevation axis emergency2-limit has been reached in the downwards direction",
     "",
     "boolean",
     ),
    ("elev-emergency2-limit-up-reached",
     "Elevation axis emergency2-limit has been reached in the upwards direction",
     "",
     "boolean",
     ),
    ("elev-enc-failed",
     "Elevation encoder has failed",
     "",
     "boolean"),
    ("elev-hard-limit-down-reached",
     "Elevation axis hard-limit has been reached in the downwards direction",
     "",
     "boolean",
     ),
    ("elev-hard-limit-up-reached",
     "Elevation axis hard-limit has been reached in the upwards direction",
     "",
     "boolean",
     ),
    ("elev-motion-error",
     "Elevation axis does not move although commanded to do so",
     "",
     "boolean",
     ),
    ("elev-motor-current",
     "Elevation motor current",
     "A",
     "float",
     "-11",
     "11"),
    ("elev-motor-overtemp",
     "Elevation motor indicates an overtemperature",
     "",
     "boolean",
     ),
    ("elev-overcurrent-error",
     ("True if the current drawn by the elevation drive exceeds the configured"
      " overcurrent threshold"),
     "",
     "boolean",
     ),
    ("elev-prelimit-down-reached",
     "Elevation axis prelimit has been reached in the downwards direction",
     "",
     "boolean",
     ),
    ("elev-prelimit-up-reached",
     "Elevation axis prelimit has been reached in the upwards direction",
     "",
     "boolean",
     ),
    ("elev-servo-failed",
     "True if any elevation axis failure occurs",
     "",
     "boolean"),
    ("elev-soft-limit-down-reached",
     "Elevation axis software limit has been reached in the downwards direction",
     "",
     "boolean",
     ),
    ("elev-soft-limit-up-reached",
     "Elevation axis software limit has been reached in the upwards direction",
     "",
     "boolean",
     ),
    ("elev-soft-prelimit-down-reached",
     "Elevation axis software prelimit has been reached in the downwards direction",
     "",
     "boolean",
     ),
    ("elev-soft-prelimit-up-reached",
     "Elevation axis software prelimit has been reached in the upwards direction",
     "",
     "boolean",
     ),
    ("failure-present",
     ("Indicates whether at least one failure that prevents antenna"
      " movement is currently latched"),
     "",
     "boolean",
     ),
    ("hatch-door-open",
     "Hatch door open or not",
     "",
     "boolean"),
    ("indexer-position",
     ("The current receiver indexer position as a discrete mapped to the"
      " receiver band it is at"),
     "",
     "discrete",
     "undefined",
     "l",
     "s",
     "moving",
     "x",
     "u",
     ),
    ("indexer-position-raw",
     "The current receiver indexer position as reported in its native format",
     "deg",
     "float",
     "0",
     "120",
     ),
    ("key-switch-emergency-limit-bypass-enabled",
     "Key switch for emergency limit override functionality is enabled or not",
     "",
     "boolean",
     ),
    ("key-switch-safe1-enabled",
     "Key switch for SAFE function in the SAFE 1 position or not",
     "",
     "boolean",
     ),
    ("key-switch-safe2-enabled",
     "Key switch for SAFE function in the SAFE 2 position or not",
     "",
     "boolean",
     ),
    ("local-time-synced",
     "Local time synced or not",
     "",
     "boolean"),
    ("lubrication-azim-bearing-ok",
     "Lubrication at the azimuth bearing ok or not",
     "",
     "boolean",
     ),
    ("lubrication-azim-gearbox-ok",
     "Lubrication at the azimuth gearbox ok or not",
     "",
     "boolean",
     ),
    ("lubrication-elev-bearing-ok",
     "Lubrication at the elevation bearing ok or not",
     "",
     "boolean",
     ),
    ("lubrication-elev-jack-ok",
     "Lubrication at the elevation jack ok or not",
     "",
     "boolean",
     ),
    ("mode",
     "Current operational mode of the AP",
     "",
     "discrete",
     "stowing",
     "star-track",
     "track",
     "stop",
     "maintenance",
     "going-to-maintenance",
     "rate",
     "shutdown",
     "e-stop",
     "stowed",
     "slew",
     ),
    ("motion-profiler-azim-enabled",
     "ACU motion profiler for azimuth axis enabled or disabled",
     "",
     "boolean",
     ),
    ("motion-profiler-elev-enabled",
     "ACU motion profiler for elevation axis enabled or disabled",
     "",
     "boolean",
     ),
    ("on-source-threshold",
     ("Current threshold value used by the 'on-source-threshold'"
      " condition to determine if on target"),
     "deg",
     "float",
     "-10000000",
     "10000000",
     ),
    ("on-target",
     "AP is on target",
     "",
     "boolean"),
    ("ped-door-open",
     "Pedestal door open or not",
     "",
     "boolean"),
    ("point-error-refraction-enabled",
     "RF refraction pointing error correction enabled or disabled",
     "",
     "boolean",
     ),
    ("point-error-systematic-enabled",
     "Systematic pointing error correction enabled or disabled",
     "",
     "boolean",
     ),
    ("point-error-tiltmeter-enabled",
     "Tiltmeter pointing error correction enabled or disabled",
     "",
     "boolean",
     ),
    ("power-24-volt-ok",
     "Internal 24V power ok (available) or not (missing)",
     "",
     "boolean",
     ),
    ("profibus-error",
     "Profibus cable interrupted or stations not responding",
     "",
     "boolean",
     ),
    ("reboot-reason",
     "Reports reason for last reboot of the ACU",
     "",
     "discrete",
     "powerfailure",
     "remote",
     "plc-watchdog",
     "other",
     ),
    ("refr-corr-elev",
     "Currently applied refraction correction in elevation ",
     "arcsec",
     "float",
     "-300",
     "300",
     ),
    ("regen-resistor-overtemp",
     ("The regeneration resistor of the power supply module for the"
      " servo amplifiers reports an overtemperature or not"),
     "",
     "boolean",
     ),
    ("requested-azim",
     "Target azimuth position",
     "deg",
     "float",
     "-185",
     "275"),
    ("requested-azim-rate",
     "Requested azimuth velocity",
     "deg/s",
     "float",
     "-2",
     "2"),
    ("requested-elev",
     "Target elevation position",
     "deg",
     "float",
     "15",
     "92"),
    ("requested-elev-rate",
     "Requested elevation velocity",
     "deg/s",
     "float",
     "-1",
     "1"),
    ("ridx-amp-failed",
     "Receiver indexer amplifier or the regeneration resistor reports a problem",
     "",
     "boolean",
     ),
    ("ridx-brake-failed",
     "Receiver indexer brake release problem occured",
     "",
     "boolean",
     ),
    ("ridx-brakes-released",
     "True if all receiver indexer axis brakes are released",
     "",
     "boolean",
     ),
    ("ridx-enc-failed",
     "Receiver indexer encoder has failed",
     "",
     "boolean"),
    ("ridx-hard-limit-ccw-reached",
     "Receiver indexer hard-limit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("ridx-hard-limit-cw-reached",
     "Receiver indexer hard-limit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("ridx-motion-error",
     "Receiver indexer axis does not move although commanded to do so",
     "",
     "boolean",
     ),
    ("ridx-motor-current",
     "Receiver indexer motor current",
     "A",
     "float",
     "-2.5",
     "2.5"),
    ("ridx-motor-overtemp",
     "Receiver indexer motor indicates an overtemperature",
     "",
     "boolean",
     ),
    ("ridx-overcurrent-error",
     ("True if the current drawn by the receiver indexer drive exceeds the"
      " configured overcurrent threshold"),
     "",
     "boolean",
     ),
    ("ridx-servo-failed",
     "True if any receiver indexer axis failure occurs",
     "",
     "boolean",
     ),
    ("ridx-soft-limit-ccw-reached",
     "Receiver indexer software limit has been reached in the counterclockwise direction",
     "",
     "boolean",
     ),
    ("ridx-soft-limit-cw-reached",
     "Receiver indexer software limit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("ridx-soft-prelimit-ccw-reached",
     ("Receiver indexer software prelimit has been reached in the"
      " counterclockwise direction"),
     "",
     "boolean",
     ),
    ("ridx-soft-prelimit-cw-reached",
     "Receiver indexer software prelimit has been reached in the clockwise direction",
     "",
     "boolean",
     ),
    ("sdc-drive-power-on",
     "Drive power supply contactor in SDC on or off",
     "",
     "boolean",
     ),
    ("sdc-power-ok",
     "Power supply of the SDC ok or not (includes detection of a missing phase)",
     "",
     "boolean",
     ),
    ("sp-pdc-surge-detected",
     "Surge protection device in PDC detected an electrical surge or not",
     "",
     "boolean",
     ),
    ("spem-corr-azim",
     ("Currently applied pointing error correction in azimuth based on"
      " systematic error model"),
     "arcsec",
     "float",
     "-3600",
     "3600",
     ),
    ("spem-corr-elev",
     ("Currently applied pointing error correction in elevation based on"
      " systematic error model"),
     "arcsec",
     "float",
     "-3600",
     "3600",
     ),
    ("stow-time-period",
     "Time period for stow after communication is lost",
     "sec",
     "integer",
     "60",
     "3600",
     ),
    ("struct-tilt-temp",
     "Temperature as reported by the tiltmeter",
     "degC",
     "float",
     "-5",
     "40",
     ),
    ("struct-tilt-x",
     "Structural tilt in X direction",
     "arcsec",
     "float",
     "-120",
     "120"),
    ("struct-tilt-y",
     "Structural tilt in Y direction",
     "arcsec",
     "float",
     "-120",
     "120"),
    ("tilt-corr-azim",
     "Currently applied pointing error correction in azimuth based on tiltmeter readout",
     "arcsec",
     "float",
     "-3600",
     "3600",
     ),
    ("tilt-corr-elev",
     ("Currently applied pointing error correction in"
      " elevation based on tiltmeter readout"),
     "arcsec",
     "float",
     "-3600",
     "3600",
     ),
    ("tilt-param-an0",
     "Currently applied parameter AN0 for average tilt of tower towards North.",
     "arcsec",
     "float",
     "-3600",
     "3600",
     ),
    ("tilt-param-aw0",
     "Currently applied parameter AW0 for average tilt of tower towards West.",
     "arcsec",
     "float",
     "-3600",
     "3600",
     ),
    ("tiltmeter-read-error",
     "Reading from the tiltmeter failed",
     "",
     "boolean"),
    ("track-stack-size",
     "Number of track samples in the ACU sample stack",
     "",
     "integer",
     "0",
     "3000",
     ),
    ("warning-horn-enabled",
     "Warning horn enabled or disabled",
     "",
     "boolean"),
    ("warning-horn-sounding",
     "Indicate if the warning horn is audibly sounding at this moment",
     "",
     "boolean",
     ),
    ("yoke-door-open",
     "Yoke door open or not",
     "",
     "boolean"),
    ("yoke-plc-ext-box-overtemp",
     "Yoke PLC extension box reports an overtemperature or not",
     "",
     "boolean",
     ),
    ("sdc-unexpected-drive-power",
     "TBD",
     "",
     "boolean"),
    ("State",
     "",
     "",
     "",
     ""),
    ("Status",
     "",
     "",
     "",
     ""),
]

EXPECTED_REQUEST_LIST = [
    ("clear-track-stack"),
    ("enable-motion-profiler"),
    ("enable-point-error-refraction"),
    ("enable-point-error-systematic"),
    ("enable-point-error-tiltmeter"),
    ("enable-warning-horn"),
    ("halt"),
    ("help"),
    ("log-level"),
    ("maintenance"),
    ("rate"),
    ("reset-failures"),
    ("restart"),
    ("set-average-tilt-an0"),
    ("set-average-tilt-aw0"),
    ("sensor-list"),
    ("sensor-sampling"),
    ("sensor-value"),
    ("set-indexer-position"),
    ("set-on-source-threshold"),
    ("set-stow-time-period"),
    ("set-weather-data"),
    ("slew"),
    ("star-track"),
    ("stop"),
    ("stow"),
    ("track"),
    ("track-az-el"),
    ("version-list"),
    ("watchdog"),
    ("init"),
    ("state"),
    ("status"),
]


class TestProxyWrapper(object):
    def __init__(self, test_instance, device_proxy):
        self.device_proxy = device_proxy
        self.test_inst = test_instance

    def assertCommandSucceeds(self, command_name, *params, **kwargs):
        """Assert that given command succeeds when called with given parameters.

        Parameters
        ----------
        command_name : str
            The name of the request.
        params : list of objects
            The parameters with which to call the request.
        """
        if params == ():
            try:
                reply = self.device_proxy.command_inout(command_name)
            except DevFailed as derr:
                reply = derr[0].desc
        else:
            try:
                if len(params) > 1:
                    command_params = params
                else:
                    command_params = params[0]
                reply = self.device_proxy.command_inout(command_name, command_params)
            except DevFailed as derr:
                reply = derr[0].desc

        reply_name = self.device_proxy.command_query(command_name).cmd_name
        self.test_inst.assertEqual(
            reply_name,
            command_name,
            "Reply to request '%s'" "has name '%s'." % (command_name, reply_name),
        )
        if reply:
            msg_reply = reply[1]
        else:
            msg_reply = "(with no error message)"

        msg = (
            "Expected command '%s' called with parameters %r to succeed, "
            "but it failed %s." % (command_name, params, ("with error '%s'" % msg_reply))
        )

        self.test_inst.assertTrue(reply is None, msg)

    def assertCommandFails(self, command_name, *params, **kwargs):
        """Assert that given command fails when called with given parameters.

        Parameters
        ----------
        command_name : str
            The name of the request.
        params : list of objects
            The parameters with which to call the request.
        """
        if params == ():
            try:
                reply = self.device_proxy.command_inout(command_name)
            except DevFailed as derr:
                reply = derr[0].desc
        else:
            if len(params) > 1:
                command_params = params
            else:
                command_params = params[0]
            try:
                reply = self.device_proxy.command_inout(command_name, command_params)
            except DevFailed as derr:
                reply = derr[0].desc

        reply_name = self.device_proxy.command_query(command_name).cmd_name
        msg = "Reply to command '%s' has name '%s'." % (command_name, reply_name)
        self.test_inst.assertEqual(reply_name, command_name, msg)
        msg = (
            "Expected command '%s' called with parameters %r to fail, "
            "but it was successful." % (command_name, params)
        )
        self.test_inst.assertFalse(reply is None, msg)

    def wait_until_attribute_equals(
        self,
        timeout,
        attr_name,
        value,
        attr_data_type=CmdArgType.DevString,
        places=7,
        pollfreq=0.02,
    ):
        """Wait until a attribute's value equals the given value, or times out.

        Parameters
        ----------
        timeout : float
            How long to wait before timing out, in seconds.
        attr_name : str
            The name of the sensor.
        value : obj
            The expected value of the sensor. Type must match sensortype.
        attr_data_type : type, optional
            The type to use to convert the sensor value.
        places : int, optional
            The number of places to use in a float comparison. Has no effect
            if sensortype is not float.
        pollfreq : float, optional
            How frequently to poll for the sensor value.

        """
        # TODO Should be changed to use some varient of SensorTransitionWaiter

        stoptime = time.time() + timeout
        success = False

        if attr_data_type == CmdArgType.DevDouble:
            def cmpfun(got, exp):
                return abs(got - exp) < 10 ** -places
        else:
            def cmpfun(got, exp):
                return got == exp
        lastval = None
        while time.time() < stoptime:
            lastval = self.device_proxy.read_attribute(attr_name).value
            if cmpfun(lastval, value):
                success = True
                break
            time.sleep(pollfreq)

        if not success:
            self.test_inst.fail(
                "Timed out while waiting %ss for %s sensor to"
                " become %s. Last value was %s." % (timeout, attr_name, value, lastval)
            )


class MkatApTangoTests(DeviceTestCase):
    external = False
    device = MkatAntennaPositioner

    def test_attribute_list_basic(self):
        """
        Test attribute list but only check the attribute names.
        """

        def get_actual_sensor_list():
            """Return the list of actual attributes of the connected device server

            The comment is w.r.t `if self.external`
            Some sensors are specific to the simulator and not specified in the
            ICD and as such should not be tested for on the KATCP interface
            of external devices.
            expected_set = set([s[0]
            for s in EXPECTED_SENSOR_LIST
            if s[0] not in ['actual-azim-rate', 'actual-elev-rate',
            'requested-azim-rate', 'requested-elev-rate']
            ])
            """
            attr_list = self.device.get_attribute_list()
            sens_list = [tangoname2katcpname(attr) for attr in attr_list]
            return sens_list

        if self.external:
            pass
        else:
            expected_set = set([s[0] for s in EXPECTED_SENSOR_LIST])
        actual_set = set(get_actual_sensor_list())

        self.assertEqual(
            actual_set,
            expected_set,
            "\n\n!Actual sensor list differs from expected list!\n\nThese sensors are"
            " missing:\n%s\n\nFound these unexpected sensors:\n%s"
            % (
                "\n".join(sorted(expected_set - actual_set)),
                "\n".join(sorted(actual_set - expected_set)),
            ),
        )

    def test_command_list(self):
        def get_actual_command_list():
            """Return the list of actual requests of the connected server"""
            command_list = self.device.command_list_query()
            req_list = [
                tangoname2katcpname(command.cmd_name.lower()) for command in command_list
            ]
            return req_list

        expected_set = set(EXPECTED_REQUEST_LIST)
        actual_set = set(get_actual_command_list())
        self.assertEqual(
            actual_set,
            expected_set,
            "\n\n!Actual request list differs from expected list!\n\nThese requests are"
            " missing:\n%s\n\nFound these unexpected requests:\n%s"
            % (
                "\n".join(sorted(expected_set - actual_set)),
                "\n".join(sorted(actual_set - expected_set)),
            ),
        )


class TestMkatAp(DeviceTestCase):
    external = False
    device = MkatAntennaPositioner

    def setUp(self):
        super(TestMkatAp, self).setUp()
        self.instance = MkatAntennaPositioner.instances[self.device.name()]
        self.client = TestProxyWrapper(self, self.device)
        if not self.external:
            # MkatApModel with faster azim and elev max rates to allow tests to execute
            # quicker.
            self.instance.ap_model.azim_drive.set_max_rate(20.0)
            self.instance.ap_model.elev_drive.set_max_rate(10.0)

        def cleanup_refs():
            del self.instance

        self.addCleanup(cleanup_refs)

    def test_rate(self):
        AZ_REQ_RATE = 1.9
        EL_REQ_RATE = 0.9
        self.client.assertCommandFails("Rate", AZ_REQ_RATE, EL_REQ_RATE)
        self.client.assertCommandSucceeds("Stop")
        self.client.assertCommandSucceeds("Rate", AZ_REQ_RATE, EL_REQ_RATE)
        self.assertEqual(self.device.mode, "rate")
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        az_req_rate = self.device.requested_azim_rate
        el_req_rate = self.device.requested_elev_rate
        self.assertEqual(az_req_rate, AZ_REQ_RATE)
        self.assertEqual(el_req_rate, EL_REQ_RATE)
        az_rate = self.device.actual_azim_rate
        el_rate = self.device.actual_elev_rate
        self.assertEqual(az_rate, AZ_REQ_RATE)
        self.assertEqual(el_rate, EL_REQ_RATE)
        print("azim-rate req=%.2f actual=%.2f" % (az_req_rate, az_rate))
        print("elev-rate req=%.2f actual=%.2f" % (el_req_rate, el_rate))
        az_pos1 = self.device.actual_azim
        el_pos1 = self.device.actual_elev
        time.sleep(1)
        az_pos2 = self.device.actual_azim
        el_pos2 = self.device.actual_elev
        self.assertTrue(az_pos2 > az_pos1)
        self.assertTrue(el_pos2 > el_pos1)
        az_rate = self.device.actual_azim_rate
        el_rate = self.device.actual_elev_rate
        print("azim-rate req=%.2f actual=%.2f" % (az_req_rate, az_rate))
        print("elev-rate req=%.2f actual=%.2f" % (el_req_rate, el_rate))
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
        self.client.assertCommandFails("Slew", AZ_REQ_POS, EL_REQ_POS)
        self.client.assertCommandSucceeds("Stop")
        self.client.assertCommandSucceeds("Slew", AZ_REQ_POS, EL_REQ_POS)
        self.assertEqual(self.device.mode, "slew")
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        az_req_pos = self.device.requested_azim
        el_req_pos = self.device.requested_elev
        self.assertEqual(az_req_pos, AZ_REQ_POS)
        self.assertEqual(el_req_pos, EL_REQ_POS)
        self.client.wait_until_attribute_equals(
            2, "on_target", 0, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            10, "on_target", 1, attr_data_type=CmdArgType.DevBoolean
        )
        azim = self.device.actual_azim
        elev = self.device.actual_elev
        self.assertAlmostEqual(az_req_pos, azim, 2)
        self.assertAlmostEqual(el_req_pos, elev, 2)
        self.client.assertCommandSucceeds("Stop")
        self.assertEqual(self.device.mode, "stop")

    def test_switch_between_track_and_slew(self):
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(1, "mode", "stop")
        self.client.assertCommandSucceeds("Track")
        self.client.wait_until_attribute_equals(1, "mode", "track")
        # Mode transitions are only allowed from STOP
        self.client.assertCommandFails("Slew", 210, 65)
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(1, "mode", "stop")
        self.client.assertCommandSucceeds("Slew", 220, 75)
        self.client.wait_until_attribute_equals(1, "mode", "slew")
        # Mode transitions are only allowed from STOP
        self.client.assertCommandFails("Track")
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(1, "mode", "stop")
        self.client.assertCommandSucceeds("Track")
        self.client.wait_until_attribute_equals(1, "mode", "track")
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(1, "mode", "stop")

    def test_track(self):
        MAX_AZIM_FOR_TEST = 250
        MAX_ELEV_FOR_TEST = 70
        MAX_TRACK_WAIT_TIME = 40  # 5s + 50samples*0.5s/sample = 30
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(2, "mode", "stop")
        azim = round(self.device.actual_azim, 3)
        elev = round(self.device.actual_elev, 3)
        if azim > MAX_AZIM_FOR_TEST:
            azim = MAX_AZIM_FOR_TEST
        if elev > MAX_ELEV_FOR_TEST:
            elev = MAX_ELEV_FOR_TEST
        # Load a few samples to track
        t0 = time.time() + 5
        for i in range(0, 50):
            # New sample every 500ms with 0.1deg movement
            self.client.assertCommandSucceeds(
                "Track_Az_El",
                t0 + (i * 0.5),
                (azim + 5) + (i * 0.1),
                (elev + 5) + (i * 0.1),
            )
        # Start tracking
        self.client.assertCommandSucceeds("Track")
        self.client.wait_until_attribute_equals(2, "mode", "track")
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            2, "on_target", 0, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            MAX_TRACK_WAIT_TIME, "on_target", 1, attr_data_type=CmdArgType.DevBoolean
        )
        # Check requested vs actual after target reached
        az_req_pos = round(self.device.requested_azim, 3)
        el_req_pos = round(self.device.requested_elev, 3)
        azim = round(self.device.actual_azim, 3)
        elev = round(self.device.actual_elev, 3)
        self.assertAlmostEqual(az_req_pos, azim, 2)
        self.assertAlmostEqual(el_req_pos, elev, 2)
        # Mode should still be track
        self.client.wait_until_attribute_equals(2, "mode", "track")
        # Add a few samples in the past (these should be ignored)
        t1 = time.time() - 200
        self.client.assertCommandSucceeds("Track_Az_El", t1, azim + 2, elev + 2)
        self.client.assertCommandSucceeds("Track_Az_El", t1 + 0.5, azim + 2.5, elev + 2.5)
        self.client.assertCommandSucceeds("Track_Az_El", t1 + 1, azim + 3, elev + 3)
        self.client.assertCommandSucceeds("Track_Az_El", t1 + 1.5, azim + 3.5, elev + 3.5)
        self.client.wait_until_attribute_equals(
            2, "on_target", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.assertAlmostEqual(az_req_pos, azim, 2)
        self.assertAlmostEqual(el_req_pos, elev, 2)
        # Add a few more samples, and check that tracking continues
        t2 = time.time() + 2
        self.client.assertCommandSucceeds("Track_Az_El", t2, azim + 2, elev + 2)
        self.client.assertCommandSucceeds("Track_Az_El", t2 + 0.5, azim + 2.5, elev + 2.5)
        self.client.assertCommandSucceeds("Track_Az_El", t2 + 1, azim + 3, elev + 3)
        self.client.assertCommandSucceeds("Track_Az_El", t2 + 1.5, azim + 3.5, elev + 3.5)
        self.client.wait_until_attribute_equals(
            2, "on_target", 1, attr_data_type=CmdArgType.DevBoolean
        )
        # Stop the drive
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(2, "mode", "stop")

    def test_stow(self):
        # Make test start nice and close to the actual stow position
        ELEV_FOR_TEST = self.instance.ap_model.STOW_ELEV - 2  # MkatApModel.STOW_ELEV - 2
        MAX_STOW_WAIT_TIME = 8
        self.instance.ap_model.elev_drive.set_position(ELEV_FOR_TEST)
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(2, "mode", "stop")
        self.client.assertCommandSucceeds("Stow")
        self.client.wait_until_attribute_equals(2, "mode", "stowing")
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(2, "mode", "stop")
        self.client.assertCommandSucceeds("Stow")
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(MAX_STOW_WAIT_TIME, "mode", "stowed")

    def test_maintenance(self):
        # Make test start nice and close to the actual maint position
        # Add a bit to the max maint wait time to account for brake activity
        AZIM_FOR_TEST = self.instance.ap_model.MAINT_AZIM - 5
        ELEV_FOR_TEST = self.instance.ap_model.MAINT_ELEV - 2
        MAX_MAINT_WAIT_TIME = 8
        self.instance.ap_model.azim_drive.set_position(AZIM_FOR_TEST)
        self.instance.ap_model.elev_drive.set_position(ELEV_FOR_TEST)
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(2, "mode", "stop")
        self.client.assertCommandSucceeds("Maintenance")
        self.client.wait_until_attribute_equals(2, "mode", "going-to-maintenance")
        self.client.assertCommandSucceeds("Stop")
        self.client.wait_until_attribute_equals(2, "mode", "stop")
        self.client.assertCommandSucceeds("Maintenance")
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            MAX_MAINT_WAIT_TIME, "mode", "maintenance"
        )

    def test_set_indexer_position(self):
        # Test for 'l'
        self.client.assertCommandSucceeds("Set_Indexer_Position", "l")
        while self.device.indexer_position == "moving":
            print("ridx-pos=%.4f" % self.device.indexer_position_raw)
            time.sleep(0.5)
        self.assertEqual(self.device.indexer_position, "l")
        self.assertAlmostEqual(self.device.indexer_position_raw, 4.0, 2)
        # Test for 'u'
        self.client.assertCommandSucceeds("Set_Indexer_Position", "u")
        while self.device.indexer_position == "moving":
            print("ridx-pos=%.4f" % self.device.indexer_position_raw)
            time.sleep(0.5)
        self.assertEqual(self.device.indexer_position, "u")
        self.assertAlmostEqual(self.device.indexer_position_raw, 6.0, 2)
        # Test for 'x'
        self.client.assertCommandSucceeds("Set_Indexer_Position", "x")
        while self.device.indexer_position == "moving":
            print("ridx-pos=%.4f" % self.device.indexer_position_raw)
            time.sleep(0.5)
        self.assertEqual(self.device.indexer_position, "x")
        self.assertAlmostEqual(self.device.indexer_position_raw, 2.0, 2)
        # Test for 's'
        self.client.assertCommandSucceeds("Set_Indexer_Position", "s")
        while self.device.indexer_position == "moving":
            print("ridx-pos=%.4f" % self.device.indexer_position_raw)
            time.sleep(0.5)
        self.assertEqual(self.device.indexer_position, "s")
        self.assertAlmostEqual(self.device.indexer_position_raw, 8.0, 2)
        # Test some invalid ridx positions
        self.client.assertCommandFails("Set_Indexer_Position", "k")
        self.assertEqual(self.device.indexer_position, "s")
        self.client.assertCommandFails("Set_Indexer_Position", "moving")
        self.assertEqual(self.device.indexer_position, "s")

    def test_set_on_source_threshold(self):
        self.client.assertCommandSucceeds("Stop")
        # Slew to a position and check that threshold is the default 1e-6
        AZ_REQ_POS = -170
        EL_REQ_POS = 20
        self.client.assertCommandSucceeds("Slew", AZ_REQ_POS, EL_REQ_POS)
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            2, "on_target", 0, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            30, "on_target", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.assertAlmostEqual(self.device.actual_azim, AZ_REQ_POS, 2)
        self.assertAlmostEqual(self.device.actual_elev, EL_REQ_POS, 2)
        self.client.assertCommandSucceeds("Stop")
        # Set new threshold and slew to a position and check that the new threshold has
        # been applied
        self.client.assertCommandSucceeds("Set_On_Source_Threshold", 1e-1)
        self.assertEqual(self.device.on_source_threshold, 1e-1)
        AZ_REQ_POS = -160
        EL_REQ_POS = 30
        self.client.assertCommandSucceeds("Slew", AZ_REQ_POS, EL_REQ_POS)
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            4, "on_target", 0, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            30, "on_target", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.assertAlmostEqual(self.device.actual_azim, AZ_REQ_POS, 0)
        self.assertAlmostEqual(self.device.actual_elev, EL_REQ_POS, 0)
        self.assertNotAlmostEqual(self.device.actual_azim, AZ_REQ_POS, 2)
        self.assertNotAlmostEqual(self.device.actual_elev, EL_REQ_POS, 2)

    def test_attribute_values(self):
        self.assertEqual(self.device.mode, "shutdown")
        self.assertEqual(self.device.requested_azim, -185.0)
        self.assertEqual(self.device.requested_elev, 15.0)
        self.assertEqual(self.device.failure_present, False)
        self.assertEqual(self.device.actual_azim, -185.0)
        self.assertEqual(self.device.actual_elev, 15.0)
        self.assertEqual(self.device.requested_azim_rate, 0.0)
        self.assertEqual(self.device.requested_elev_rate, 0.0)
        self.assertEqual(self.device.actual_azim_rate, 0.0)
        self.assertEqual(self.device.actual_elev_rate, 0.0)
        self.assertEqual(self.device.State(), DevState.ON)
        self.assertEqual(self.device.Status(), "The device is in ON state.")

    def test_stop(self):
        self.assertEqual(self.device.mode, "shutdown")
        self.client.assertCommandFails("Slew", 78, 23)
        self.assertNotEqual(self.device.mode, "stop")
        self.assertEqual(self.device.mode, "shutdown")
        self.client.assertCommandSucceeds("Stop")
        self.assertEqual(self.device.mode, "stop")
        self.client.assertCommandSucceeds("Slew", 89, 89)
        self.assertNotEqual(self.device.mode, "stop")
        self.client.assertCommandSucceeds("Stow")
        self.client.wait_until_attribute_equals(
            3, "azim_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            3, "elev_brakes_released", 1, attr_data_type=CmdArgType.DevBoolean
        )
        self.client.wait_until_attribute_equals(
            11, "mode", "stowed", attr_data_type=CmdArgType.DevString
        )
        self.assertNotEqual(self.device.mode, "stop")
        self.client.assertCommandSucceeds("Stop")
        self.assertEqual(self.device.mode, "stop")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
