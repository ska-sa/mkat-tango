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

import time
import threading
import enum
import Queue
from functools import partial

from katcp.core import Sensor, Message
from katcp.kattypes import (
    inform, request, return_reply, Discrete, Float, Timestamp, Str, Int, Bool)
from katcp.core import ProtocolFlags
from katcore.dev_base import ThreadedModel, Device
from katcore.sim_base import SimTestDevice
from katversion import build_info

# Preconfigure the handler decorators to use KATCP v5.
inform = partial(inform, major=5)
request = partial(request, major=5)
return_reply = partial(return_reply, major=5)

class _ApSimEnum(object):
    """Base class for AP enumerated types (private to this AP simulator module)."""
    @classmethod
    def get_items_as_list(cls):
        """Retrieves list of class attributes (in this case the enumerated values).

        Returns
        -------
        rslt : list
            List of the class attributes (i.e. enumerated values)
        """
        return [v for k,v in cls.__dict__.iteritems() if not k.startswith('_')]

class ApOperMode(_ApSimEnum):
    """Class specifying an enumerated type for the Operational Mode of the AP."""
    shutdown = "shutdown"
    stop = "stop"
    stowing = "stowing"
    stowed = "stowed"
    gtm = "going-to-maintenance"
    maint = "maintenance"
    rate = "rate"
    slew = "slew"
    track = "track"
    star_track = "star-track"
    estop = "e-stop"

class ApControlMode(_ApSimEnum):
    """Class specifying an enumerated type for the Control Mode of the AP."""
    safe1 = "safe1"
    safe2 = "safe2"
    remote = "remote"
    local = "local"
    manual = "manual"

class ApRidxPosition(_ApSimEnum):
    """Class specifying an enumerated type for the AP receiver indexer positions."""
    x = 'x'
    l = 'l'
    u = 'u'
    s = 's'
    moving = "moving"
    undefined = "undefined"

class ApRebootReason(_ApSimEnum):
    """Class specifying an enumerated type for the reasons of the last ACU reboot."""
    powerfailure = 'powerfailure'
    plc_watchdog = 'plc-watchdog'
    remote = 'remote'
    other = 'other'

class ApSplineStatus(_ApSimEnum):
    """Class specifying an enumerated type for the status of ACU spline interpolation."""
    green = 'green'
    yellow = 'yellow'
    red = 'red'

class EStopReason(_ApSimEnum):
    """Class specifying an enumerated type for the various emergency stop reasons."""
    ler = "ler"
    outside_ped = "outside-pedestal"
    az_wrap = "az-cable-wrap"
    azel_drives = "azel-drives"
    ridx_drives = "ri-drives"
    pcu = "pcu"
    local = "local"
    none = "none"

class MkatApModel(ThreadedModel):
    """A model of the antenna used by the antenna positioner simulator."""

    UPDATE_PERIOD = 0.1
    AZIM_DRIVE_MAX_RATE = 2.0
    ELEV_DRIVE_MAX_RATE = 1.0
    RIDX_DRIVE_MAX_RATE = 2.0
    STOW_ELEV = 90.0
    MAINT_AZIM = 90.0
    MAINT_ELEV = 25.0
    WARN_HORN_SOUND_TIME = 5  # Real ACU is 10s

    def __init__(self):
        """Create a model for antenna positioner simulator."""

        super(MkatApModel, self).__init__()

        sensors = [
            Sensor(Sensor.DISCRETE, "mode", "Current operational mode of the AP",
                   "", ApOperMode.get_items_as_list()),
            Sensor(Sensor.DISCRETE, "control", "Current control mode of the AP",
                   "", ApControlMode.get_items_as_list()),
            Sensor(Sensor.BOOLEAN, "failure-present",
                   "Indicates whether at least one failure that prevents antenna "
                   "movement is currently latched", ""),
            Sensor(Sensor.DISCRETE, "reboot-reason",
                   "Reports reason for last reboot of the ACU",
                   "", ApRebootReason.get_items_as_list()),
            Sensor(Sensor.FLOAT, "actual-azim", "Actual azimuth position",
                   "deg", [-185.0, 275.0]),
            Sensor(Sensor.FLOAT, "actual-elev", "Actual elevation position",
                   "deg", [15.0, 92.0]),
            Sensor(Sensor.FLOAT, "requested-azim", "Target azimuth position",
                   "deg", [-185.0, 275.0]),
            Sensor(Sensor.FLOAT, "requested-elev", "Target elevation position",
                   "deg", [15.0, 92.0]),
            Sensor(Sensor.FLOAT, "temperature-sensor1",
                   "The value from the first temperature sensor installed in the "
                   "antenna tower of AP#1 only.",
                   "degC", [-5, 45]),
            Sensor(Sensor.FLOAT, "temperature-sensor2",
                   "The value from the second temperature sensor installed in the "
                   "antenna tower of AP#1 only.",
                   "degC", [-5, 45]),
            Sensor(Sensor.FLOAT, "temperature-sensor3",
                   "The value from the third temperature sensor installed in the "
                   "antenna tower of AP#1 only.",
                   "degC", [-5, 45]),
            Sensor(Sensor.FLOAT, "temperature-sensor4",
                   "The value from the fourth temperature sensor installed in the "
                   "antenna tower of AP#1 only.",
                   "degC", [-5, 45]),
            Sensor(Sensor.FLOAT, "struct-tilt-x", "Structural tilt in X direction",
                   "arcsec", [-120.0, 120.0]),
            Sensor(Sensor.FLOAT, "struct-tilt-y", "Structural tilt in Y direction",
                   "arcsec", [-120.0, 120.0]),
            Sensor(Sensor.FLOAT, "struct-tilt-temp",
                   "Temperature as reported by the tiltmeter", "degC", [-5.0, 40.0]),
            Sensor(Sensor.FLOAT, "tilt-corr-azim",
                   "Currently applied pointing error correction in azimuth "
                   "based on tiltmeter readout", "arcsec", [-3600.0, 3600.0]),
            Sensor(Sensor.FLOAT, "tilt-corr-elev",
                   "Currently applied pointing error correction in elevation "
                   "based on tiltmeter readout", "arcsec", [-3600.0, 3600.0]),
            Sensor(Sensor.FLOAT, "spem-corr-azim",
                    "Currently applied pointing error correction in azimuth "
                   "based on systematic error model", "arcsec", [-3600.0, 3600.0]),
            Sensor(Sensor.FLOAT, "spem-corr-elev",
                   "Currently applied pointing error correction in elevation "
                   "based on systematic error model", "arcsec", [-3600.0, 3600.0]),
            Sensor(Sensor.FLOAT, "refr-corr-elev",
                   "Currently applied refraction correction in elevation ",
                   "arcsec", [-300.0, 300.0]),
            Sensor(Sensor.DISCRETE, "indexer-position",
                   "The current receiver indexer position as a discrete mapped "
                   "to the receiver band it is at", "",
                   ApRidxPosition.get_items_as_list()),
            Sensor(Sensor.FLOAT, "indexer-position-raw",
                   "The current receiver indexer position as reported in its "
                   "native format", "deg", [0.0, 120.0]),
            Sensor(Sensor.BOOLEAN, "local-time-synced",
                   "Indicates whether the local time of the AP is synchronised to the "
                   "master time reference", ""),
            Sensor(Sensor.BOOLEAN, "hatch-door-open", "Hatch door open or not", ""),
            Sensor(Sensor.BOOLEAN, "ped-door-open", "Pedestal door open or not", ""),
            Sensor(Sensor.BOOLEAN, "yoke-door-open", "Yoke door open or not", ""),
            Sensor(Sensor.INTEGER, "stow-time-period",
                   "Time period for stow after communication is lost", "sec",
                   [60, 3600]),
            Sensor(Sensor.BOOLEAN, "cb-pdc-power-ridb-closed",
                   "RIDB power supply circuit breaker (CB2) in PDC open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-receiver1-closed",
                   "Receiver1 circuit breaker (CB4) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-receiver2-closed",
                   "Receiver2 circuit breaker (CB5) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-receiver3-closed",
                   "Receiver3 circuit breaker (CB6) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-receiver4-closed",
                   "Receiver4 circuit breaker (CB7) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-digitiser1-closed",
                   "Digitiser1 circuit breaker (CB8) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-digitiser2-closed",
                   "Digitiser2 circuit breaker (CB9) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-digitiser3-closed",
                   "Digitiser3 circuit breaker (CB10) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-digitiser4-closed",
                   "Digitiser4 circuit breaker (CB11) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-ridb-vacuum-pump-closed",
                   "Vacuum pump circuit breaker (CB12) in RIDB open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-pdc-ler-ingest-fan-closed",
                   "LER Ingest Fan circuit breaker (CB14) in PDC open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-pdc-he-compressor-closed",
                   "Helium Compressor circuit breaker (CB17) in PDC open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-sdc-fans-closed",
                   "SDC Fans circuit breaker (CB21) in SDC open or closed", ""),
            Sensor(Sensor.BOOLEAN, "cb-sdc-recv-controller-closed",
                   "Receiver Controller circuit breaker (CB23) in SDC open or closed",
                   ""),
            Sensor(Sensor.BOOLEAN, "cb-sdc-brake-power-closed",
                   "Brake Power Supply circuit breaker (CB27) in SDC open or closed",
                   ""),
            Sensor(Sensor.BOOLEAN, "cb-sdc-servo-amp-power-closed",
                   "Servo Amplifier Power Supply circuit breaker (CB26) in SDC open or "
                   "closed", ""),
            Sensor(Sensor.BOOLEAN, "sdc-drive-power-on",
                   "Drive power supply contactor in SDC on or off", ""),
            Sensor(Sensor.BOOLEAN, "cb-dc-sdc-general-closed",
                   "General DC circuit breaker located in SDC open or closed", ""),
            Sensor(Sensor.BOOLEAN, "sp-pdc-surge-detected",
                   "Surge protection device in PDC detected an electrical surge or not",
                   ""),
            Sensor(Sensor.BOOLEAN, "point-error-systematic-enabled",
                   "Systematic pointing error correction enabled or disabled", ""),
            Sensor(Sensor.BOOLEAN, "point-error-tiltmeter-enabled",
                   "Tiltmeter pointing error correction enabled or disabled", ""),
            Sensor(Sensor.BOOLEAN, "point-error-refraction-enabled",
                   "RF refraction pointing error correction enabled or disabled",
                   ""),
            Sensor(Sensor.BOOLEAN, "warning-horn-enabled",
                   "Warning horn enabled or disabled", ""),
            Sensor(Sensor.FLOAT, "on-source-threshold",
                   "Current threshold value used by the 'on-source-threshold' "
                   "condition to determine if on target", "deg", [-10.0e6, 10.0e6]),
            Sensor(Sensor.DISCRETE, "e-stop-reason",
                   "Reason for the occurrence of an emergency stop", "",
                   EStopReason.get_items_as_list()),
            Sensor(Sensor.BOOLEAN, "sdc-power-ok",
                   "Power supply of the SDC ok or not (includes detection of a missing "
                   "phase)", ""),
            Sensor(Sensor.BOOLEAN, "power-24-volt-ok",
                   "Internal 24V power ok (available) or not (missing)", ""),
            Sensor(Sensor.BOOLEAN, "cabinet-breakers-all-ok",
                   "Not ok if at least one of the automatic breakers inside the "
                   "drive cabinet has tripped", ""),
            Sensor(Sensor.BOOLEAN, "cabinet-overtemp-all-ok",
                   "Not ok if one of the overtemperature sensors in the drive "
                   "cabinet reports an alarm", ""),
            Sensor(Sensor.BOOLEAN, "acu-plc-interface-error",
                   "ACU detected communication error between ACU and PLC", ""),
            Sensor(Sensor.BOOLEAN, "profibus-error",
                   "Profibus cable interrupted or stations not responding", ""),
            Sensor(Sensor.BOOLEAN, "tiltmeter-read-error",
                   "Reading from the tiltmeter failed", ""),
            Sensor(Sensor.BOOLEAN, "azim-plc-ext-box-overtemp",
                   "Azimuth PLC extension box reports an overtemperature or not", ""),
            Sensor(Sensor.BOOLEAN, "yoke-plc-ext-box-overtemp",
                   "Yoke PLC extension box reports an overtemperature or not", ""),
            Sensor(Sensor.BOOLEAN, "drive-power-supply-failed",
                   "The power supply module for the servo amplifiers failed or "
                   "indicate an overtemperature", ""),
            Sensor(Sensor.BOOLEAN, "regen-resistor-overtemp",
                   "The regeneration resistor of the power supply module for the "
                   "servo amplifiers reports an overtemperature or not", ""),
            Sensor(Sensor.BOOLEAN, "key-switch-safe1-enabled",
                   "Key switch for SAFE function in the SAFE 1 position or not", ""),
            Sensor(Sensor.BOOLEAN, "key-switch-safe2-enabled",
                   "Key switch for SAFE function in the SAFE 2 position or not", ""),
            Sensor(Sensor.BOOLEAN, "key-switch-emergency-limit-bypass-enabled",
                   "Key switch for emergency limit override functionality is "
                   "enabled or not", ""),
            Sensor(Sensor.BOOLEAN, "on-target",
                    "Reports True if the total position error (i.e. actual position vs "
                    "calculated position) is below the 'on-source-threshold'", ""),
            Sensor(Sensor.BOOLEAN, "acu-speed-limited",
                   "Due to excessive power requirements, the maximum velocities "
                   "have been reduced", ""),
            Sensor(Sensor.DISCRETE, "acu-spline-status",
                   "Status relating to the number of track samples that are "
                   "currently available in the ACU stack (green=optimal)", "",
                   ApSplineStatus.get_items_as_list()),
            Sensor(Sensor.BOOLEAN, "lubrication-azim-bearing-ok",
                   "Lubrication at the azimuth bearing ok or not", ""),
            Sensor(Sensor.BOOLEAN, "lubrication-azim-gearbox-ok",
                   "Lubrication at the azimuth gearbox ok or not", ""),
            Sensor(Sensor.BOOLEAN, "lubrication-elev-bearing-ok",
                   "Lubrication at the elevation bearing ok or not", ""),
            Sensor(Sensor.BOOLEAN, "lubrication-elev-jack-ok",
                   "Lubrication at the elevation jack ok or not", ""),
            Sensor(Sensor.BOOLEAN, "azim-prelimit-cw-reached",
                   "Azimuth axis prelimit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-prelimit-ccw-reached",
                   "Azimuth axis prelimit has been reached in the counterclockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-prelimit-up-reached",
                   "Elevation axis prelimit has been reached in the upwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-prelimit-down-reached",
                   "Elevation axis prelimit has been reached in the downwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-hard-limit-cw-reached",
                   "Azimuth axis hard-limit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-hard-limit-ccw-reached",
                   "Azimuth axis hard-limit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-hard-limit-up-reached",
                   "Elevation axis hard-limit has been reached in the upwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-hard-limit-down-reached",
                   "Elevation axis hard-limit has been reached in the downwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "ridx-hard-limit-cw-reached",
                   "Receiver indexer hard-limit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "ridx-hard-limit-ccw-reached",
                   "Receiver indexer hard-limit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-emergency-limit-cw-reached",
                   "Azimuth axis emergency-limit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-emergency-limit-ccw-reached",
                   "Azimuth axis emergency-limit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-emergency-limit-up-reached",
                   "Elevation axis emergency-limit has been reached in the upwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-emergency-limit-down-reached",
                   "Elevation axis emergency-limit has been reached in the "
                   "downwards direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-emergency2-limit-cw-reached",
                   "Azimuth axis emergency2-limit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-emergency2-limit-ccw-reached",
                   "Azimuth axis emergency2-limit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-emergency2-limit-up-reached",
                   "Elevation axis emergency2-limit has been reached in the upwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-emergency2-limit-down-reached",
                   "Elevation axis emergency2-limit has been reached in the "
                   "downwards direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-soft-limit-cw-reached",
                   "Azimuth axis software limit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-soft-limit-ccw-reached",
                   "Azimuth axis software limit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-soft-limit-down-reached",
                   "Elevation axis software limit has been reached in the downwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-soft-limit-up-reached",
                   "Elevation axis software limit has been reached in the upwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "ridx-soft-limit-cw-reached",
                   "Receiver indexer software limit has been reached in the "
                   "clockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "ridx-soft-limit-ccw-reached",
                   "Receiver indexer software limit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-soft-prelimit-cw-reached",
                   "Azimuth axis software prelimit has been reached in the clockwise "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-soft-prelimit-ccw-reached",
                   "Azimuth axis software prelimit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-soft-prelimit-down-reached",
                   "Elevation axis software prelimit has been reached in the downwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "elev-soft-prelimit-up-reached",
                   "Elevation axis software prelimit has been reached in the upwards "
                   "direction", ""),
            Sensor(Sensor.BOOLEAN, "ridx-soft-prelimit-cw-reached",
                   "Receiver indexer software prelimit has been reached in the "
                   "clockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "ridx-soft-prelimit-ccw-reached",
                   "Receiver indexer software prelimit has been reached in the "
                   "counterclockwise direction", ""),
            Sensor(Sensor.BOOLEAN, "azim-servo-failed",
                   "True if any azimuth axis failure occurs", ""),
            Sensor(Sensor.BOOLEAN, "elev-servo-failed",
                   "True if any elevation axis failure occurs", ""),
            Sensor(Sensor.BOOLEAN, "ridx-servo-failed",
                   "True if any receiver indexer axis failure occurs", ""),
            Sensor(Sensor.BOOLEAN, "azim-brake1-failed",
                   "Azimuth brake 1 release problem occured", ""),
            Sensor(Sensor.BOOLEAN, "azim-brake2-failed",
                   "Azimuth brake 2 release problem occured", ""),
            Sensor(Sensor.BOOLEAN, "elev-brake-failed",
                   "Elevation brake release problem occured", ""),
            Sensor(Sensor.BOOLEAN, "ridx-brake-failed",
                   "Receiver indexer brake release problem occured", ""),
            Sensor(Sensor.BOOLEAN, "azim-amp1-failed",
                   "Azimuth amplifier 1 or the regeneration resistor reports a problem",
                   ""),
            Sensor(Sensor.BOOLEAN, "azim-amp2-failed",
                   "Azimuth amplifier 2 or the regeneration resistor reports a problem",
                   ""),
            Sensor(Sensor.BOOLEAN, "elev-amp-failed",
                   "Elevation amplifier or the regeneration resistor reports a problem",
                   ""),
            Sensor(Sensor.BOOLEAN, "ridx-amp-failed",
                   "Receiver indexer amplifier or the regeneration resistor "
                   "reports a problem", ""),
            Sensor(Sensor.BOOLEAN, "azim-motor1-overtemp",
                   "Azimuth motor 1 indicates an overtemperature", ""),
            Sensor(Sensor.BOOLEAN, "azim-motor2-overtemp",
                   "Azimuth motor 2 indicates an overtemperature", ""),
            Sensor(Sensor.BOOLEAN, "elev-motor-overtemp",
                   "Elevation motor indicates an overtemperature", ""),
            Sensor(Sensor.BOOLEAN, "ridx-motor-overtemp",
                   "Receiver indexer motor indicates an overtemperature", ""),
            Sensor(Sensor.BOOLEAN, "azim-aux1-mode-selected",
                   "Azimuth axis auxiliary1 mode activated or not (i.e. azimuth only "
                   "driven by motor 1", ""),
            Sensor(Sensor.BOOLEAN, "azim-aux2-mode-selected",
                   "Azimuth axis auxiliary2 mode activated or not (i.e. azimuth only "
                   "driven by motor 2", ""),
            Sensor(Sensor.BOOLEAN, "azim-enc-failed",
                   "Azimuth encoder has failed", ""),
            Sensor(Sensor.BOOLEAN, "elev-enc-failed",
                   "Elevation encoder has failed", ""),
            Sensor(Sensor.BOOLEAN, "ridx-enc-failed",
                   "Receiver indexer encoder has failed", ""),
            Sensor(Sensor.BOOLEAN, "azim-range-switch-failed",
                   "Azimuth range switch signal is not as expected at either "
                   "the azimuth travel limits or in the non-ambiguous range", ""),
            Sensor(Sensor.BOOLEAN, "azim-motion-error",
                   "Azimuth axis does not move although commanded to do so", ""),
            Sensor(Sensor.BOOLEAN, "elev-motion-error",
                   "Elevation axis does not move although commanded to do so", ""),
            Sensor(Sensor.BOOLEAN, "ridx-motion-error",
                   "Receiver indexer axis does not move although commanded to do so", ""),
            Sensor(Sensor.BOOLEAN, "azim-brakes-released",
                   "True if all azimuth axis brakes are released", ""),
            Sensor(Sensor.BOOLEAN, "elev-brakes-released",
                   "True if all elevation axis brakes are released", ""),
            Sensor(Sensor.BOOLEAN, "ridx-brakes-released",
                   "True if all receiver indexer axis brakes are released", ""),
            Sensor(Sensor.BOOLEAN, "azim-overcurrent-error",
                   "True if the current drawn by the azimuth drive exceeds the "
                   "configured overcurrent threshold", ""),
            Sensor(Sensor.BOOLEAN, "elev-overcurrent-error",
                   "True if the current drawn by the elevation drive exceeds the "
                   "configured overcurrent threshold", ""),
            Sensor(Sensor.BOOLEAN, "ridx-overcurrent-error",
                   "True if the current drawn by the receiver indexer drive exceeds the "
                   "configured overcurrent threshold", ""),
            Sensor(Sensor.BOOLEAN, "amp-power-cycle-interlocked",
                   "True if waiting time presently applies because there has been "
                   "too many power cycles of the main contactor for one of the "
                   "drives",
                   ""),
            Sensor(Sensor.BOOLEAN, "can-bus-failed",
                   "Failure detected on ACU and servo amplifiers CAN bus", ""),
            Sensor(Sensor.DISCRETE, "device-status",
                   "Summary of the Antenna Positioner operational status", "",
                   ["ok", "degraded", "fail"]),
            Sensor(Sensor.BOOLEAN, "warning-horn-sounding",
                   "True if the warning horn is currently sounding", ""), 
            Sensor(Sensor.BOOLEAN, "motion-profiler-azim-enabled",
                   "Reports whether the motion profiler for the azimuth axis "
                   "is enabled or disabled", ""),
            Sensor(Sensor.BOOLEAN, "motion-profiler-elev-enabled",
                   "Reports whether the motion profiler for the elevation axis "
                   "is enabled or disabled", ""),
            Sensor(Sensor.BOOLEAN, "sdc-unexpected-drive-power",
                   "Indicate if the drive is behaving unexpectedly, e.g. "
                   "if the sdc-drive-power-on is enabled when it should not be", ""),
            Sensor(Sensor.FLOAT, "azim-motor1-current",
                   "The current value of azimuth motor #1",
                   "A", [-11.0, 11.0]),
            Sensor(Sensor.FLOAT, "azim-motor2-current",
                   "The current value of azimuth motor #2",
                   "A", [-11.0, 11.0]),
            Sensor(Sensor.FLOAT, "elev-motor-current",
                   "The current value of the elevation motor",
                   "A", [-11.0, 11.0]),
            Sensor(Sensor.FLOAT, "ridx-motor-current",
                   "The current value of the receiver indexer motor",
                   "A", [-2.5, 2.5]),
            Sensor(Sensor.FLOAT, "tilt-param-an0",
                   "Currently applied parameter AN0 for average tilt of tower towards North",
                   "arcsec", [-3600.0, 3600.0]),
            Sensor(Sensor.FLOAT, "tilt-param-aw0",
                   "Currently applied parameter AW0 for average tilt of tower towards West",
                   "arcsec", [-3600.0, 3600.0]),
            Sensor(Sensor.INTEGER, "track-stack-size",
                   "The number of track samples available in the ACU sample stack",
                   "", [0, 3000]),

            # Simulator specific sensors (not specified in the ICD)
            Sensor(Sensor.FLOAT, "actual-azim-rate", "Actual azimuth velocity",
                   "deg/s", [-self.AZIM_DRIVE_MAX_RATE, self.AZIM_DRIVE_MAX_RATE]),
            Sensor(Sensor.FLOAT, "actual-elev-rate", "Actual elevation velocity",
                   "deg/s", [float(-self.ELEV_DRIVE_MAX_RATE),
                       float(self.ELEV_DRIVE_MAX_RATE)]),
            Sensor(Sensor.FLOAT, "requested-azim-rate", "Requested azimuth velocity",
                   "deg/s", [-self.AZIM_DRIVE_MAX_RATE, self.AZIM_DRIVE_MAX_RATE]),
            Sensor(Sensor.FLOAT, "requested-elev-rate", "Requested elevation velocity",
                   "deg/s", [-self.ELEV_DRIVE_MAX_RATE, self.ELEV_DRIVE_MAX_RATE]),
        ]

        for sensor in sensors:
            self.sensors[sensor.name] = sensor
            # Set the value at least once so that the status is nominal
            sensor.set_value(sensor.value())

        # Initial values
        self.set_mode(ApOperMode.shutdown)
        self.get_sensor("control").set_value("remote")
        self.get_sensor("device-status").set_value("ok")
        self.get_sensor("acu-spline-status").set_value("red")
        self.get_sensor("stow-time-period").set_value(10*60)  # 10 minutes
        self.get_sensor("indexer-position").set_value(ApRidxPosition.l)
        self.get_sensor("on-source-threshold").set_value(1e-3)
        self.get_sensor("e-stop-reason").set_value(EStopReason.none)
        self.get_sensor("actual-azim").set_value(0)
        self.get_sensor("actual-elev").set_value(90)

        # Cached values of selected state and mode for detecting whether a
        # sensor update has changed the sensor value
        self._last_mode = self.mode()
        self._last_control = self.control()

        # Objects for driving the antenna
        azim_sensors = {
            "actual": self.sensors["actual-azim"],
            "requested": self.sensors["requested-azim"],
            "actual-rate": self.sensors["actual-azim-rate"],
        }

        elev_sensors = {
            "actual": self.sensors["actual-elev"],
            "requested": self.sensors["requested-elev"],
            "actual-rate": self.sensors["actual-elev-rate"],
        }

        ridx_sensors = {
            "actual": self.sensors["indexer-position-raw"],
            "requested": Sensor(Sensor.FLOAT, "dummy-req-ridx-pos-raw", "", "",
                                [0.0, 10.0]),
            "actual-rate": Sensor(Sensor.FLOAT, "dummy-ridx-rate", "", "",
                                  [-self.RIDX_DRIVE_MAX_RATE, self.RIDX_DRIVE_MAX_RATE]),
        }

        self.azim_drive = Drive(azim_sensors, self.get_sensor("on-source-threshold").value())
        self.elev_drive = Drive(elev_sensors, self.get_sensor("on-source-threshold").value())
        self.ridx_drive = Drive(ridx_sensors, 1e-3)

        # Initial values for boolean sensors
        for sensor in sensors:
            if sensor.stype == "boolean":
                if sensor.name.startswith("cb-"):
                    # Circuit breaker sensors are nominal when 1 (i.e. closed)
                    self.get_sensor(sensor.name).set_value(True)
                elif sensor.name.endswith("-ok"):
                    # Sensor names ending with '-ok' are by definition nominal 1
                    self.get_sensor(sensor.name).set_value(True)
                else:
                    self.get_sensor(sensor.name).set_value(False)

        self.get_sensor("local-time-synced").set_value(True)
        # Warning horn is always enabled by default at real ACU but for the
        # simulator a default of disabled makes more sense
        self.get_sensor("warning-horn-enabled").set_value(False)

        # Register sensors to be observed
        for sensor in sensors:
            if sensor.name in ["mode", "on-source-threshold"]:
                sensor.attach(self)

        ## Define local class variables ##
        # Define variable which indicates if a ridx move request is being processed
        self._is_ridx_request_busy = False
        # Define variable that holds the requested ridx position while moving
        self._requested_ridx_pos = ApRidxPosition.l

    def _is_on_target(self):
        return (self.azim_drive.at_requested_position() and
                self.elev_drive.at_requested_position())

    def _is_moving(self):
        return self.azim_drive.is_moving() or self.elev_drive.is_moving()

    def stopped(self):
        return (self.get_sensor("mode").value() in
                ["shutdown", "stop", "stowed", "maintenance", "e-stop"])

    def mode(self):
        return self.get_sensor("mode").value()

    def control(self):
        return self.get_sensor("control").value()

    def in_remote_control(self):
        """Check if the model is in the remote control mode.

        Returns
        -------
        in_remote : bool
            True if model is in remote control mode
        """
        in_remote = self.control() in [ApControlMode.remote]
        return in_remote

    def set_mode(self, new_mode, status=Sensor.NOMINAL):
        if bool(self.get_sensor("warning-horn-sounding").value()):
            print "Cannot set mode! Warning horn sounding."
            return
        mode_sensor = self.get_sensor("mode")
        current_mode = mode_sensor.value()
        #print "AP mode", curent_mode, "->", new_mode
        if current_mode != new_mode:
            mode_sensor.set_value(new_mode, status)
        # Simulate the warning horn delay if enabled - on real ACU mode is
        # first set and warning horn then sounds.
        if (current_mode in ["stowed", "maintenance", "shutdown"] and
                new_mode == "stop"):
            if bool(self.get_sensor("warning-horn-enabled").value()):
                self.get_sensor("warning-horn-sounding").set_value(True)
                self._warning_horn_time_t0 = time.time()

    def set_ridx_position(self, ridx_pos):
        """Request to select receiver indexer position.

        Parameters
        ----------
        ridx_pos : Discrete(("x", "l", "u", "s"))
            The receiver indexer position to select
        """
        # Note: Not the actual positions (thumb suck values for simulation purposes)
        self._requested_ridx_pos = ridx_pos
        if ridx_pos == ApRidxPosition.x:
            pos = 2.0
        elif ridx_pos == ApRidxPosition.l:
            pos = 4.0
        elif ridx_pos == ApRidxPosition.u:
            pos = 6.0
        elif ridx_pos == ApRidxPosition.s:
            pos = 8.0
        else:
            pos = 0
        if pos != 0:
            self.ridx_drive.set_requested_position(pos)
            self.ridx_drive.set_mode(Drive.MODE.slew)
            self.get_sensor("indexer-position").set_value(ApRidxPosition.moving)
            self._is_ridx_request_busy = True

    def set_az_el(self, timestamp, az_deg, el_deg):
        """Specify a desired pointing direction with timestamp.

        Parameters
        ----------
        timestamp : KATCP Timestamp
            The time when the position coordinates should be applied
        az_deg : float
            Azimuth coordinate (degrees)
        el_deg : float
            Elevation coordinate (degrees)
        """
        self.azim_drive.set_pointing(timestamp, az_deg)
        self.elev_drive.set_pointing(timestamp, el_deg)

    def rate(self, az_rate, el_rate):
        # Update the requested rate sensors
        self.get_sensor("requested-azim-rate").set_value(az_rate)
        self.get_sensor("requested-elev-rate").set_value(el_rate)
        # Set the requested rates on the drives
        self.azim_drive.set_rate(az_rate)
        self.elev_drive.set_rate(el_rate)
        # Activate rate mode
        self.set_mode(ApOperMode.rate)

    def slew(self, az, el):
        # Set the requested position on the azim and elev drives
        # (will also set the sensor values)
        self.azim_drive.set_requested_position(az)
        self.elev_drive.set_requested_position(el)
        # Activate slew mode
        self.set_mode(ApOperMode.slew)

    def reset_failures(self):
        """Reset any failure flags that are currently set."""
        # TODO(TA): HAS TO BE DONE MANUALLY

    def update(self, sensor, reading):
        """
        Respond to update messages regarding sensor changes of sensors registered to
        be observed.
        """
        value = reading[2]
        if sensor.name == "mode" and value != self._last_mode:
            if value == ApOperMode.stop:
                self.azim_drive.set_mode(Drive.MODE.stop)
                self.elev_drive.set_mode(Drive.MODE.stop)
            elif value == ApOperMode.track:
                self.azim_drive.set_mode(Drive.MODE.track)
                self.elev_drive.set_mode(Drive.MODE.track)
            elif value == ApOperMode.slew:
                self.azim_drive.set_mode(Drive.MODE.slew)
                self.elev_drive.set_mode(Drive.MODE.slew)
            elif value == ApOperMode.rate:
                self.azim_drive.set_mode(Drive.MODE.rate)
                self.elev_drive.set_mode(Drive.MODE.rate)
            elif value == ApOperMode.stowing:
                # Set the elevation stow position and slew the elevation drive to it
                self.elev_drive.set_requested_position(self.STOW_ELEV)
                self.elev_drive.set_mode(Drive.MODE.slew)
                # Azimuth drive does not need to move, but ensure it is on_target
                self.azim_drive.set_requested_position(self.azim_drive.get_position())
                self.azim_drive.set_mode(Drive.MODE.slew)
            elif value == ApOperMode.estop:
                pass # Don't do anything
            elif value == ApOperMode.gtm:
                # Set the maintenance position (arbitrary, don't know what it should be)
                self.azim_drive.set_requested_position(self.MAINT_AZIM)
                self.elev_drive.set_requested_position(self.MAINT_ELEV)
                self.azim_drive.set_mode(Drive.MODE.slew)
                self.elev_drive.set_mode(Drive.MODE.slew)
            else:
                pass
            self._last_mode = value
        elif sensor.name == "on-source-threshold":
            self.azim_drive.set_at_requested_position_threshold(value)
            self.elev_drive.set_at_requested_position_threshold(value)
        else:
            pass

    def run(self):
        """
        Background thread which is responsible for polling the drive objects for
        updating drives angles. This function also updates the 'on-target' sensor
        and handles the transitions to 'maintenace' and 'stowed' modes when the
        desired position has been reached. In addition it also takes care of some
        receiver indexer transition logic.
        """
        while not self._stopEvent.is_set():
            # Warning horn sounding check
            if bool(self.get_sensor("warning-horn-sounding").value()):
                if (time.time() > self._warning_horn_time_t0 +
                        self.WARN_HORN_SOUND_TIME):
                    self.get_sensor("warning-horn-sounding").set_value(False)
                else:
                    #print "Warning horn sounding ..."
                    continue
            # Azel drives refresh and transition logic
            if self.stopped():
                pass  # Do nothing (idle)
            else:
                timestamp = time.time()
                self.azim_drive.refresh_position(timestamp)
                self.elev_drive.refresh_position(timestamp)
                on_target_sensor = self.get_sensor("on-target")
                if self._is_on_target() != on_target_sensor.value():
                    on_target_sensor.set_value(self._is_on_target())
                if self.mode() == ApOperMode.stowing:
                    if not self._is_moving():
                        self.set_mode(ApOperMode.stowed)
                elif self.mode() == ApOperMode.gtm:
                    if not self._is_moving():
                        self.set_mode(ApOperMode.maint)
                else:
                    pass
            # Ridx drive refresh and transition logic
            if self._is_ridx_request_busy:
                timestamp = time.time()
                self.ridx_drive.refresh_position(timestamp)
                if not self.ridx_drive.is_moving():
                    self.get_sensor("indexer-position").set_value(
                        self._requested_ridx_pos)
                    self._is_ridx_request_busy = False
            self._stopEvent.wait(self.UPDATE_PERIOD)
        self._stopEvent.clear()


class Control(object):
    """Implements the actual feedback control calculation.

    The feeback is implemented using a simple Proportional Control Loop.

    Parameters
    ----------
    Kp : float
        The proportional constant value
    """

    def __init__(self, Kp=2.0):
        """Control constructor."""
        self.Kp = Kp

        # Experimental PID values
        self.Ki=0.5
        self.Kd=1.0
        self.derivator=0
        self.integrator=0
        self.integrator_max=500
        self.integrator_min=-500

    def control_signal(self, requested, actual):
        """Calculate the necessary control signal given the desired and actual values.

        Parameters
        ----------
        requested : float
            The desired value
        actual : float
            The actual measured value

        Returns
        -------
        return : float
            The calculated control signal
        """
        error = requested - actual
        return self.Kp * error
        #return self.control_signal_PID(requested, actual)

    def control_signal_PI(self, requested, actual):
        """
        Calculate PI output value for given reference input and feedback (Experimental)
        """

        self.error = requested - actual

        self.P_value = self.Kp * self.error

        self.integrator = self.integrator + self.error

        if self.integrator > self.integrator_max:
                self.integrator = self.integrator_max
        elif self.integrator < self.integrator_min:
                self.integrator = self.integrator_min

        self.I_value = self.integrator * self.Ki

        PID = self.P_value + self.I_value

        return PID

    def control_signal_PID(self, requested, actual):
        """
        Calculate PID output value for given reference input and feedback (Experimental)
        """

        self.error = requested - actual

        self.P_value = self.Kp * self.error
        self.D_value = self.Kd * ( self.error - self.derivator)
        self.derivator = self.error

        self.integrator = self.integrator + self.error

        if self.integrator > self.integrator_max:
                self.integrator = self.integrator_max
        elif self.integrator < self.integrator_min:
                self.integrator = self.integrator_min

        self.I_value = self.integrator * self.Ki

        PID = self.P_value + self.I_value + self.D_value

        return PID


class Drive(object):
    """Simulates a servomotor drive with units 'degrees'.

    Parameters
    ----------
    """

    MODE = enum.Enum("stop", "rate", "slew", "track")

    def __init__(self, sensors, at_req_pos_threshold=1e-6):
        self._pos_deg = sensors["actual"]
        self._req_pos_deg = sensors["requested"]
        self._vel_deg_s = sensors["actual-rate"]
        self._at_req_pos_threshold = at_req_pos_threshold
        self._min_pos_deg = self._pos_deg.params[0]
        self._max_pos_deg = self._pos_deg.params[1]
        self._max_vel_deg_s = self._vel_deg_s.params[1]
        self._mode = self.MODE.stop
        self._prev_time = 0  # Last time the drive was refreshed (used to calculate rate)
        self._at_req_pos = False  # Is current position equal to requested position
        self._controller = Control()  # Controller object used in TRACK and SLEW modes
        self._limit_cw_reached = False
        self._limit_ccw_reached = False
        # Variables used only in TRACK mode
        self._pointing_samples = []
        self._curr_sample_timestamp = 0
        # Init the actual and requested sensors with nominal values that always start
        # at the minimum drive position (important for initial limit checks)
        self._pos_deg.set_value(self._min_pos_deg)
        self._req_pos_deg.set_value(self._req_pos_deg.params[0])

    def __str__(self):
        if self._mode == self.MODE.track:
            s = "%s t=%.3f rate=%.2f req_pos=%.4f pos=%.4f, at_req_pos=%s" % (self._mode,
                    time.time(), self._vel_deg_s.value(), self._req_pos_deg.value(),
                    self._pos_deg.value(), self._at_req_pos)
        elif self._mode == self.MODE.slew:
            s = "%s rate=%.2f req_pos=%.4f pos=%.4f" % (self._mode,
                    self._vel_deg_s.value(), self._req_pos_deg.value(),
                    self._pos_deg.value())
        else:
            s = "%s rate=%.2f pos=%.4f" % (self._mode,
                    self._vel_deg_s.value(), self._pos_deg.value())
        return s

    def _update_position(self, timestamp):
        time_diff = timestamp - self._prev_time
        self._prev_time = timestamp
        temp_pos_deg = self._pos_deg.value() + (time_diff * self._vel_deg_s.value())
        if temp_pos_deg < self._min_pos_deg:
            self._limit_ccw_reached = True
            self._pos_deg.set_value(self._min_pos_deg, Sensor.WARN, timestamp)
        elif temp_pos_deg > self._max_pos_deg:
            self._limit_cw_reached = True
            self._pos_deg.set_value(self._max_pos_deg, Sensor.WARN, timestamp)
        else:
            self._limit_cw_reached = False
            self._limit_ccw_reached = False
            self._pos_deg.set_value(temp_pos_deg, Sensor.NOMINAL, timestamp)
        #print self

    def _almost_equal(self, x, y, abs_threshold=1e-6):
        return abs(x - y) <= abs_threshold

    def _drive_at_rate(self, timestamp):
        self._at_req_pos = False
        self._update_position(timestamp)

    def _drive_to_position(self, timestamp):
        # Note: The current controller does not allow for a smooth linear
        # transition between points, but is rather follows an inverse
        # exponential decay curve (i.e. fast start, slow end)
        self.set_rate(
            self._controller.control_signal(
                self._req_pos_deg.value(), self._pos_deg.value()
            )
        )
        self._update_position(timestamp)
        # Check if at requested position
        if self._almost_equal(self._req_pos_deg.value(), self._pos_deg.value(),
                self._at_req_pos_threshold):
            self._at_req_pos = True
            self.set_mode(self.MODE.stop)
        else:
            self._at_req_pos = False
        # If limit reached then stop, can go no further
        if self.at_limit()[0]:
            self.set_mode(self.MODE.stop)

    def _drive_track(self, timestamp):
        if timestamp > self._curr_sample_timestamp:
            # Remove samples with a timestamp in the past. Proxy guarantees
            # ascending timestamp order, so these should be at the front and
            # not affected by new samples appended to the end.
            old_samples = [
                (t, deg) for (t, deg) in self._pointing_samples if t < timestamp
            ]
            del(self._pointing_samples[0:len(old_samples)])
            try:
                # Get the next pointing sample, if one exists
                temp_sample = self._pointing_samples.pop(0)
                self._curr_sample_timestamp = temp_sample[0]
                self._req_pos_deg.set_value(temp_sample[1])
            except IndexError:
                # If no pointing samples, keep drive where it is at
                pass
        # Note: The current controller does not allow for a smooth linear
        # transition between points, but is rather follows an inverse
        # exponential decay curve (i.e. fast start, slow end)
        self.set_rate(self._controller.control_signal(self._req_pos_deg.value(),
                      self._pos_deg.value()))
        self._update_position(timestamp)
        # Check if at requested position
        if self._almost_equal(self._req_pos_deg.value(), self._pos_deg.value(),
                              self._at_req_pos_threshold):
            self._at_req_pos = True
        else:
            self._at_req_pos = False

    def get_mode(self):
        return self._mode

    def get_position(self):
        return self._pos_deg.value()

    def set_position(self, new_pos_val):
        """Useful function for testing purposes to quickly jump to a position"""
        t = time.time()
        self._pos_deg.set_value(new_pos_val, Sensor.NOMINAL, t)
        self._req_pos_deg.set_value(new_pos_val, Sensor.NOMINAL, t)
        self._at_req_pos = True

    def get_rate(self):
        return self._vel_deg_s.value()

    def set_mode(self, new_mode):
        if new_mode in self.MODE and self._mode != new_mode:
            self._mode = new_mode
            self._prev_time = time.time()
            if self._mode == self.MODE.stop:
                self.set_rate(0)
            return True
        else:
            return False

    def set_rate(self, rate):
        # Limit the rate to the maximum allowed
        if rate > self._max_vel_deg_s:
            rate = self._max_vel_deg_s
        elif rate < -self._max_vel_deg_s:
            rate = -self._max_vel_deg_s
        else:
            pass
        self._vel_deg_s.set_value(rate)

    def set_max_rate(self, max_rate):
        """Override the maximum velocity - useful for testing purposes."""
        self._max_vel_deg_s = abs(max_rate)

    def set_at_requested_position_threshold(self, new_at_req_pos_threshold):
        self._at_req_pos_threshold = new_at_req_pos_threshold

    def set_requested_position(self, new_req_pos_deg):
        """Directly specify a desired angle (for 'slew' mode)."""
        self._req_pos_deg.set_value(new_req_pos_deg)

    def set_pointing(self, timestamp, requested_deg):
        """
        Specify a pointing sample - a desired angle with corresponding timestamp.
        This is put into a list for later processing.
        """
        self._pointing_samples.append((timestamp, requested_deg))

    def clear_pointing_samples(self):
        self._pointing_samples[:] = []

    def at_requested_position(self):
        return self._at_req_pos

    def at_limit(self):
        is_at_limit = self._limit_cw_reached or self._limit_ccw_reached
        return (is_at_limit, self._limit_cw_reached, self._limit_ccw_reached)

    def is_moving(self):
        is_vel_zero = self._almost_equal(self._vel_deg_s.value(), 0.0)
        is_moving = not is_vel_zero and not self.at_limit()[0]
        return is_moving

    def refresh_position(self, timestamp):
        """
        This method should be called periodically from the model with the current
        timestamp.
        """
        if self._mode == self.MODE.stop:
            pass  # Do nothing (idle)
        elif self._mode == self.MODE.rate:
            self._drive_at_rate(timestamp)
        elif self._mode == self.MODE.slew:
            self._drive_to_position(timestamp)
        elif self._mode == self.MODE.track:
            self._drive_track(timestamp)
        else:
            # No error mode, so just go to stop
            self.set_mode(self.MODE.stop)


class MkatApDevice(Device):
    """An antenna server simulator."""

    # Indicate that this is a katcp v5 device
    PROTOCOL_INFO = ProtocolFlags(5, 0, set([
        ProtocolFlags.MULTI_CLIENT,
        ProtocolFlags.MESSAGE_IDS,
        ]))

    # Interface version information.
    VERSION_INFO = ("mkat-ap", 1, 0)

    # Device server build / instance information.
    BUILD_INFO = build_info("mkat-ap-simulator", module=__name__)

    def __init__(self, *args, **kwargs):
        """Create an MkatApDevice."""
        super(MkatApDevice, self).__init__(*args, **kwargs)

        # Remove request handlers that come from the superclass that are not on
        # the real device
        del self._request_handlers['sensor-sampling-clear']
        del self._request_handlers['client-list']

        # Cached values of mode and state for detecting whether a sensor update
        # has changed the sensor value
        self._last_mode = self._model.mode()
        self._last_control = self._model.control()

    def on_client_connect(self, req):
        """
        Inform client of build state, version, control mode and operational mode
        on connect.
        """
        super(MkatApDevice, self).on_client_connect(req)
        self.inform(req, Message.inform("mkat-ap-plc-version", "0.1"))
        self.inform(req, Message.inform("control-mode", self._model.control()))
        self.inform(req, Message.inform("operational-mode", self._model.mode()))

    def setup_sensors(self):
        """Go through all sensors defined in the model and add it to the device."""
        for sensor in self._model.sensors.values():
            self.add_sensor(sensor)
            if sensor.name == "mode":
                sensor.attach(self)
            if sensor.name == "control":
                sensor.attach(self)

    def update(self, sensor, reading):
        """Send informs when state or mode changes.

        Parameters
        ----------
        sensor : katcp.Sensor
            The sensor that will be checked for any changes in its value
        """
        value = reading[2]
        if sensor.name == "mode" and value != self._last_mode:
            self.mass_inform(Message.inform("mode", value))
            self._last_mode = value
        if sensor.name == "control" and value != self._last_control:
            self.mass_inform(Message.inform("control", value))
            self._last_control = value

    @request()
    @return_reply()
    def request_stop(self, req):
        """Request mode stop.

        If current mode is 'shutdown' or 'stow' or 'maintenance' then the
        warning horn will sound for 10 seconds if it is enabled.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.set_mode(ApOperMode.stop)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request()
    @return_reply()
    def request_stow(self, req):
        """Request mode stow.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            if (self._model.mode() in [ApOperMode.shutdown, ApOperMode.stowing,
                    ApOperMode.stowed, ApOperMode.estop]):
                reply = ["fail", "Antenna is in '%s' mode." % self._model.mode()]
            else:
                # Transit through "stowing" to "stowed"
                self._model.set_mode(ApOperMode.stowing)
                reply = ["ok"]
        else:
            reply = ["fail", "Antenna is not in remote control."]
        return reply

    @request()
    @return_reply()
    def request_maintenance(self, req):
        """Request mode maintenance.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            if self._model.mode() in [ApOperMode.gtm, ApOperMode.maint]:
                reply = ["fail", "Antenna is in '%s' mode." % self._model.mode()]
            elif self._model.mode() not in [ApOperMode.stop]:
                reply = ["fail", "Antenna mode '%s' != 'stop'." % self._model.mode()]
            else:
                # Transit through "going-to-maintenance" to "maintenance"
                self._model.set_mode(ApOperMode.gtm)
                reply = ["ok"]
        else:
            reply = ["fail", "Antenna is not in remote control."]
        return reply

    @request(Float(min=-MkatApModel.AZIM_DRIVE_MAX_RATE,
        max=MkatApModel.AZIM_DRIVE_MAX_RATE), Float(min=-MkatApModel.ELEV_DRIVE_MAX_RATE,
        max=MkatApModel.ELEV_DRIVE_MAX_RATE))
    @return_reply()
    def request_rate(self, req, azim_rate, elev_rate):
        """Request the AP to move the antenna at the rate specified.

        Parameters
        ----------
        azim_rate : float
            Azimuth velocity (degrees/sec)
        elev_rate : float
            Elevation velocity (degrees/sec)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            if self._model.mode() not in [ApOperMode.stop]:
                reply = ["fail", "Antenna mode '%s' != 'stop'." % self._model.mode()]
            else:
                self._model.rate(azim_rate, elev_rate)
                reply = ['ok']
        else:
            reply = ["fail", "Antenna is not in remote control."]
        return reply

    @request(Float(min=-185.0, max=275.0), Float(min=15.0, max=92.0))
    @return_reply()
    def request_slew(self, req, azim, elev):
        """Request the AP to slew.

        Request the AP to move (slew) the antenna to the position specified by
        the azimuth and elevation parameters.

        Parameters
        ----------
        azim : float
            Azimuth coordinate (degrees)
        elev : float
            Elevation coordinate (degrees)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            if self._model.mode() not in [ApOperMode.stop, ApOperMode.slew,
                                          ApOperMode.track]:
                reply = ["fail", "Unable to switch Antenna mode to 'slew' while in "
                                 "mode '%s'" % self._model.mode()]
            else:
                self._model.slew(azim, elev)
                reply = ['ok']
        else:
            reply = ["fail", "Antenna is not in remote control."]
        return reply

    @request(Float(min=0, max=23.999999), Float(min=-90.0, max=90.0))
    @return_reply()
    def request_star_track(self, req, asc, dec):
        """Request the AP to star-track.

        Request the AP to track a specific astronomical object with the
        specified right ascension and declination coordinates.

        Parameters
        ----------
        asc : float
            Right ascention (hours)
        dec : float
            Declination (degrees)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            if self._model.mode() not in [ApOperMode.stop]:
                reply = ["fail", "Antenna mode '%s' != 'stop'." % self._model.mode()]
            else:
                # Note: 'star-track' mode not simulated
                self._model.set_mode(ApOperMode.star_track)
                reply = ['ok']
        else:
            reply = ["fail", "Antenna is not in remote control."]
        return reply

    @request(Timestamp(), Float(min=-185.0, max=275.0), Float(min=15.0, max=92.0))
    @return_reply()
    def request_track_az_el(self, req, timestamp, azim, elev):
        """Request to provide azimuth and elevation samples to the AP.

        Request the AP to set the antenna at the position specified by the
        azimuth and elevation parameters at a specified time.

        Parameters
        ----------
        timestamp : KATCP Timestamp
            The time when the position coordinates should be applied
        azim : float
            Azimuth coordinate (degrees)
        elev : float
            Elevation coordinate (degrees)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.set_az_el(timestamp, azim, elev)
            return ['ok']
        else:
            return ["fail", "Antenna is not in remote control."]

    @request()
    @return_reply()
    def request_track(self, req):
        """Request the AP to track.

        Request the AP to start tracking using the position samples provided
        by the track-az-el request. track a specific astronomical object with
        the specified right ascension and declination coordinates.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            if self._model.mode() not in [ApOperMode.stop, ApOperMode.slew,
                                          ApOperMode.track]:
                reply = ["fail", "Unable to switch Antenna mode to 'track' while in "
                                 "mode '%s'" % self._model.mode()]
            else:
                self._model.set_mode(ApOperMode.track)
                reply = ['ok']
        else:
            reply =  ["fail", "Antenna is not in remote control."]
        return reply

    @request(Discrete([i for i in ApRidxPosition.get_items_as_list() if i != "moving"]))
    @return_reply()
    def request_set_indexer_position(self, req, ridx_pos):
        """Request to select receiver indexer position.

        Parameters
        ----------
        ridx_pos : Discrete(("x", "l", "u", "s"))
            The receiver indexer position to select

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.set_ridx_position(ridx_pos)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request(Int(min=60, max=3600))
    @return_reply()
    def request_set_stow_time_period(self, req, time_period):
        """Request to set time period for stow after communication is lost.

        Parameters
        ----------
        time_period : integer
            The time period for stow after communication is lost (seconds)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.get_sensor("stow-time-period").set_value(time_period)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request(Bool())
    @return_reply()
    def request_enable_point_error_systematic(self, req, enable):
        """
        Request to enable/disable the systematic pointing error model
        compensation provided by the ACU.

        Parameters
        ----------
        enable : bool
            Flag indicating whether this pointing error compensation should be
            enabled.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.get_sensor("point-error-systematic-enabled").set_value(enable)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request(Bool())
    @return_reply()
    def request_enable_point_error_tiltmeter(self, req, enable):
        """
        Request to enable/disable the compensation for deformation of the
        antenna provided by the ACU.

        Parameters
        ----------
        enable : bool
            Flag indicating whether this pointing error compensation should be
            enabled.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.get_sensor("point-error-tiltmeter-enabled").set_value(enable)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request(Bool())
    @return_reply()
    def request_enable_point_error_refraction(self, req, enable):
        """
        Request to enable/disable the compensation for RF refraction provided
        by the ACU.

        Parameters
        ----------
        enable : bool
            Flag indicating whether this pointing error compensation should be
            enabled.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.get_sensor("point-error-refraction-enabled").set_value(enable)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request()
    @return_reply()
    def request_enable_warning_horn(self, req):
        """Request to enable the antenna warning horn.

        Request to enable the audible alarm which sounds prior to movement of
        the antenna (i.e. release of brakes). By default the warning horn is
        enabled. Due to safety concerns, it is not possible to disable the
        warning horn.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.get_sensor("warning-horn-enabled").set_value(True)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request(Float(min=0.0, max=1.0))
    @return_reply()
    def request_set_on_source_threshold(self, req, threshold):
        """Request to set the threshold for the "not-on-source" condition.

        Parameters
        ----------
        threshold : float
            The new threshold value to set for the "not-on-source" condition
            (degrees)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.get_sensor("on-source-threshold").set_value(threshold)
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request(Float(min=0.0, max=330.0), Float(min=0.0, max=2000.0), Float(min=0.0, max=100.0))
    @return_reply()
    def request_set_weather_data(self, req, temp, pressure, humidity):
        """Request to set the weather data used by the refraction correction.

        The RF refraction compensation requires temperature, air pressure and
        humidity values.

        Parameters
        ----------
        temp : float
            The current temperature value (degC)
        pressure : float
            The current air pressure value (mbar)
        humidity : float
            The current humidity value (%)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            # Do nothing - not simulated
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request()
    @return_reply()
    def request_reset_failures(self, req):
        """Request informing the AP to clear/acknowledge any failures.

        All safety relevant failures are latched and the AP requires a command
        to clear/acknowledge the existing failures.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if self._model.in_remote_control():
            self._model.reset_failures()
            return ["ok"]
        else:
            return ["fail", "Antenna is not in remote control."]

    @request()
    @return_reply()
    def request_clear_track_stack(self, req):
        """Clear the stack with the track samples.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.azim_drive.clear_pointing_samples()
        self._model.elev_drive.clear_pointing_samples()
        return ["ok"]

    @request(Discrete(["azim", "elev"]), Bool())
    @return_reply()
    def request_enable_motion_profiler(self, req, axis, enable):
        """
        Request to enable/disable the motion profiler
        provided by the ACU for the selected movement axis.

        Parameters
        ----------
        axis : Discrete( "azim", "elev" )
            Axis for which the motion profiler should be enabled or
            disabled.
        enable : bool
            Flag indicating whether the motion profiler should be
            enabled.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        if axis == "azim":
            self.get_sensor("motion-profiler-azim-enabled").set_value(enable)
        elif axis == "elev":
            self.get_sensor("motion-profiler-elev-enabled").set_value(enable)
        else:
            reply =  ["fail", "Could not enable motion profiler"]
        return ["ok"]

    @request(Float(min=-3600, max=3600))
    @return_reply()
    def request_set_average_tilt_an0(self, req, an0):
        """
	Request to set the average tilt of antenna tower
	(towards North) which is subtracted from tiltmeter readout
	in order to avoid duplicate compensation.

        Parameters
        ----------
        an0 : float
            The average tilt of antenna tower towards north as determined by pointing
	    calibration measurements over longer time periods.
            (arc-seconds)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        return ["ok"]

    @request(Float(min=-3600, max=3600))
    @return_reply()
    def request_set_average_tilt_aw0(self, req, aw0):
        """
	Request to set the average tilt of antenna tower
	(towards West) which is subtracted from tiltmeter readout
	in order to avoid duplicate compensation.

        Parameters
        ----------
        aw0 : float
            The average tilt of antenna tower towards west as determined by pointing
	    calibration measurements over longer time periods.
            (arc-seconds)

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        # Not simulated, just return ok
        return ["ok"]


class MkatApTestDevice(SimTestDevice):
    """A test interface to the MeerKAT Antenna Positioner simulator."""

    ## @brief Interface version information.
    VERSION_INFO = ("mkat-ap-test", 0, 1)

    ## @brief Device server build / instance information.
    BUILD_INFO = build_info("mkat-ap-simulator", module=__name__)

    @request(Discrete(ApControlMode.get_items_as_list()))
    @return_reply()
    def request_set_selected_control_mode(self, req, control_mode):
        """Set the selected control_mode.

        Parameters
        ----------
        control_mode : Discrete value as defined by `ApControlMode`
            Possible control modes are: safe1 | safe2 | remote | local | manual

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        current = self._model.control()
        if current != control_mode:
            self.get_sensor("control").set_value(control_mode)
            return ["ok"]
        else:
            return ["fail", "Already at control mode '%s'" % current]

    @request(Discrete(EStopReason.get_items_as_list()))
    @return_reply()
    def request_set_e_stop(self, req, estop_reason):
        """Set AP operational mode to EStop with the appropriate reason.

        Parameters
        ----------
        estop_reason: Discrete value as defined by `EStopReason`
            Possible control modes are:
            "ler" | "outside-pedestal" | "az-cable-wrap" | "azel-drives" |
            "ri-drives" | "pcu" | "local" | "none"

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self.get_sensor("mode").set_value(ApOperMode.estop)
        self.get_sensor("e-stop-reason").set_value(estop_reason)
        return ["ok"]

    @request()
    @return_reply()
    def request_disable_warning_horn(self, req):
        """Disable the warning horn.

        This is not possible from the main AP KATCP interface.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self.get_sensor("warning-horn-enabled").set_value(False)
        return ["ok"]

    @request()
    @return_reply()
    def request_clear_e_stop(self, req):
        """Clear an existing EStop condition by going to Stop.

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self.get_sensor("mode").set_value(ApOperMode.stop)
        self.get_sensor("e-stop-reason").set_value(EStopReason.none)
        return ["ok"]

    @request(Float())
    @return_reply()
    def request_set_max_rate_azim_drive(self, req, max_rate):
        """Override the maximum azimuth drive velocity.

        Parameters
        ----------
        max_rate: float
            New maximum velocity of azimuth drive

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.azim_drive.set_max_rate(max_rate)
        return ["ok"]

    @request(Float())
    @return_reply()
    def request_set_max_rate_elev_drive(self, req, max_rate):
        """Override the maximum elevation drive velocity.

        Parameters
        ----------
        max_rate: float
            New maximum velocity of elevation drive

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.elev_drive.set_max_rate(max_rate)
        return ["ok"]

    @request(Float())
    @return_reply()
    def request_set_max_rate_ridx_drive(self, req, max_rate):
        """Override the maximum receiver indexer drive velocity.

        Parameters
        ----------
        max_rate: float
            New maximum velocity of receiver indexer drive

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.ridx_drive.set_max_rate(max_rate)
        return ["ok"]

    @request(Float())
    @return_reply()
    def request_set_azim_drive_position(self, req, new_pos_deg):
        """Set the current azimuth drive simulated position.

        Parameters
        ----------
        new_pos_deg: float
            New position value to set

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.azim_drive.set_position(new_pos_deg)
        return ["ok"]

    @request(Float())
    @return_reply()
    def request_set_elev_drive_position(self, req, new_pos_deg):
        """Set the current elevation drive simulated position.

        Parameters
        ----------
        new_pos_deg: float
            New position value to set

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.elev_drive.set_position(new_pos_deg)
        return ["ok"]

    @request(Float())
    @return_reply()
    def request_set_ridx_drive_position(self, req, new_pos_deg):
        """Set the current receiver indexer drive simulated position.

        Parameters
        ----------
        new_pos_deg: float
            New position value to set

        Returns
        -------
        success : 'ok' | 'fail' message
            Whether the request succeeded
        """
        self._model.ridx_drive.set_position(new_pos_deg)
        return ["ok"]
