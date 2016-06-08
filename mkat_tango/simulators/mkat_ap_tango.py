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
import logging
import weakref

from katproxy.sim.mkat_ap import MkatApModel, ApOperMode

from PyTango.server import Device, DeviceMeta, command, server_run
from PyTango import AttrWriteType, DevState
from PyTango import Attr, DevString, DevBoolean, DevDouble, DevVarDoubleArray, DevULong
from PyTango import UserDefaultAttrProp, Except, ErrSeverity

MODULE_LOGGER = logging.getLogger(__name__)


class MkatAntennaPositioner(Device):
    __metaclass__ = DeviceMeta
    instances = weakref.WeakValueDictionary()

    COMMAND_ERROR_REASON = "MkatAntennaPositioner_CommandFailed"
    COMMAND_ERROR_DESC_OFF = "Device in an OFF State"

    def init_device(self):
        Device.init_device(self)
        self.set_state(DevState.ON)

        self.ap_model = MkatApModel()
        self.ap_model.start()

        name = self.get_name()
        self.instances[name] = self

    def initialize_dynamic_attributes(self):
        sensors = self.ap_model.get_sensors()
        for sensor in sensors:
            #MODULE_LOGGER.debug("Adding mkat_ap sensor %r", sensor.name)
            attr_props = UserDefaultAttrProp()  # Used to set the attribute default properties
            sensor_name = formatter(sensor.name)
            method_call_read = None
            method_call_write = None

            if sensor.stype == "boolean":
                attr = Attr(sensor_name, DevBoolean, AttrWriteType.READ)
                method_call_read = self.read_attr
            elif sensor.stype == "float":
                if sensor.name.startswith('requested-'):
                    attr = Attr(sensor_name, DevDouble, AttrWriteType.READ_WRITE)
                    method_call_write = self.write_attr
                else:
                    attr = Attr(sensor_name, DevDouble, AttrWriteType.READ)
                method_call_read = self.read_attr
                attr_props.set_min_value(str(sensor.params[0]))
                attr_props.set_max_value(str(sensor.params[1]))
            elif sensor.stype == "integer":
                if sensor.name.startswith('requested-'):
                    attr = Attr(sensor_name, DevULong, AttrWriteType.READ_WRITE)
                    method_call_write = self.write_attr
                else:
                    attr = Attr(sensor_name, DevULong, AttrWriteType.READ)
                method_call_read = self.read_attr
                attr_props.set_min_value(str(sensor.params[0]))
                attr_props.set_max_value(str(sensor.params[1]))
            elif sensor.stype == "discrete":
                attr = Attr(sensor_name, DevString)
                method_call_read = self.read_attr

            attr_props.set_label(sensor.name)
            attr_props.set_description(sensor.description)
            attr_props.set_unit(sensor.units)
            attr.set_default_properties(attr_props)

            self.add_attribute(attr, method_call_read, method_call_write)

    def read_attr(self, attr):
        self.info_stream("Reading attribute %s", attr.get_name())
        sensor_name = unformatter(attr.get_name())
        sensor = self.ap_model.get_sensor(sensor_name)
        attr.set_value(sensor.value())

    def write_attr(self, attr):
        pass

    @command
    def Stop(self):
        """Request mode stop.

        If current mode is 'shutdown' or 'stow' or 'maintenance' then the
        warning horn will sound for 10 seconds if it is enabled.

        Parameters
        ==========
        None.

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote.
        """
        command_name = "Stop()"
        if self.ap_model.in_remote_control():
            self.ap_model.set_mode(ApOperMode.stop)
            MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON,
                                   "Antenna is not in remote control", command_name,
                                   ErrSeverity.WARN)

    @command
    def Maintenance(self):
        """Request mode maintenance.

        Parameters
        ==========
        None.

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If control mode is not remote or if operating mode is
                                   'gtm' or 'maint' or if operating mode is not 'stop'.
        """
        command_name = "Maintenance()"
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() in [ApOperMode.gtm, ApOperMode.maint]:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is"
                                       "in '%s' mode." % self.ap_model.mode(),
                                       command_name, ErrSeverity.WARN)
            elif self.ap_model.mode() not in [ApOperMode.stop]:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna mode "
                                       "'{}' != 'stop'.".format(self.ap_model.mode()),
                                        command_name, ErrSeverity.WARN)
            else:
                self.ap_model.set_mode(ApOperMode.gtm)
                MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON,
                                   "Antenna is not in remote control", command_name,
                                   ErrSeverity.WARN)

    @command
    def Stow(self):
        """Request mode stow.

        Parameters
        ==========
        None.

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote or ACU operating mode is
                                   not any one of; shutdown, stowing, stowed, or estop.
        """
        command_name = "Stow()"
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() in [ApOperMode.shutdown, ApOperMode.stowing,
                                        ApOperMode.stowed, ApOperMode.estop]:
                Except.throw_exception(self.COMMAND_ERROR_REASON,
                                       "Fail, Antenna is in '%s' mode."
                                       % self.ap_model.mode(), command_name,
                                       ErrSeverity.WARN)
            else:
                self.ap_model.set_mode(ApOperMode.stowing)
                MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command(dtype_in=DevVarDoubleArray)
    def Slew(self, azim_elev_coordinates):
        """Request the AP to slew.

        Request the AP to move (slew) the antenna to the position specified by
        the azimuth and elevation parameters.

        Parameters
        ==========
        azim : float
            Azimuth coordinate (degrees)
        elev : float
            Elevation coordinate (degrees)

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote or ACU operating mode is not
                                   any one of ['stop', 'slew', 'track'].
        """
        command_name = "Slew()"
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() not in [ApOperMode.stop, ApOperMode.slew,
                                            ApOperMode.track]:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Unable to "
                                       "switch Antenna mode to 'slew' while in mode"
                                       "'%s'" % self.ap_model.mode(), command_name,
                                       ErrSeverity.WARN)
            else:
                requested_azim, requested_elev = azim_elev_coordinates
                self.ap_model.slew(requested_azim, requested_elev)
                MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command
    def Clear_Track_Stack(self):
        """Clear the stack with the track samples.

        Parameters
        ==========
        None.

        Returns
        =======
        None.
        """
        self.ap_model.azim_drive.clear_pointing_samples()
        self.ap_model.elev_drive.clear_pointing_samples()

    @command(dtype_in=DevBoolean)
    def Enable_Point_Error_Refraction(self, enable):
        """
        Request to enable/disable the compensation for RF refraction provided
        by the ACU.

        Parameters
        ==========
        enable : bool
            Flag indicating whether this pointing error compensation should be
            enabled.

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote.
        """
        command_name = "Enable_Point_Error_Refraction()"
        if self.ap_model.in_remote_control():
            self.ap_model.get_sensor("point-error-refraction-enabled").set_value(enable)
            MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command(dtype_in=DevVarDoubleArray)
    def Rate(self, azim_elev_rates):
        """Request the AP to move the antenna at the rate specified.

        Parameters
        ==========
        azim_elev_rates: PyTango.DevVarDoubleArray (eqiuvalent to a numpy.ndarry)
            index 0 = azim_rate : float
                          Azimuth velocity (degrees/sec)
            index 1 = elev_rate : float
                          Elevation velocity (degrees/sec)

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote or ACU operating mode is not
                                   stop.
        """
        command_name = "Rate()"
        azim_rate, elev_rate = azim_elev_rates
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() not in [ApOperMode.stop]:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna mode"
                                       "'%s' != 'stop'." % self.ap_model.mode(),
                                       command_name, ErrSeverity.WARN)
            else:
                self.ap_model.rate(azim_rate, elev_rate)
                MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command
    def Reset_Failures(self):
        """Request informing the AP to clear/acknowledge any failures.

        All safety relevant failures are latched and the AP requires a command
        to clear/acknowledge the existing failures.

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote.
        """
        command_name = "Reset_Failures()"
        if self.ap_model.in_remote_control():
            self.ap_model.reset_failures()
            MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command(dtype_in=DevString)
    def Set_Indexer_Position(self, ridx_pos):
        """Request to select receiver indexer position.

        Parameters
        ==========
        ridx_pos : Discrete(("x", "l", "u", "s"))
            The receiver indexer position to select

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote or an invalid indexer
                                   position is given.
        """
        command_name = "Set_Indexer_Position()"
        if ridx_pos not in ["x", "l", "u", "s"]:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Illegal indexer positions '%s'" %ridx_pos,
                                   command_name, ErrSeverity.WARN)
        else:
            if self.ap_model.in_remote_control():
                self.ap_model.set_ridx_position(ridx_pos)
                MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
            else:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command(dtype_in=DevDouble)
    def Set_On_Source_Threshold(self, threshold):
        """Request to set the threshold for the "not-on-source" condition.

        Parameters
        ==========
        threshold : PyTango.DevDouble
            The new threshold value to set for the "not-on-source" condition
            (degrees)

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote.
        """
        command_name = "Set_On_Source_Threshold()"
        if self.ap_model.in_remote_control():
            self.ap_model.get_sensor("on-source-threshold").set_value(threshold)
            MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command
    def Track(self):
        """Request the AP to track.

        Request the AP to start tracking using the position samples provided
        by the track-az-el request. track a specific astronomical object with
        the specified right ascension and declination coordinates.

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote or ACU operating mode is not
                                   any of ['stop', 'slew', track'].
        """
        command_name = "Track()"
        if self.ap_model.in_remote_control():
            if self.ap_model.mode() not in [ApOperMode.stop, ApOperMode.slew,
                                          ApOperMode.track]:
                Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Unable to "
                                       "switch Antenna mode to 'track' while in "
                                       "mode '%s'" % self.ap_model.mode(), command_name,
                                        ErrSeverity.WARN)
            else:
                self.ap_model.set_mode(ApOperMode.track)
                MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

    @command(dtype_in=DevVarDoubleArray)
    def Track_Az_El(self, timestamp_azim_elev):
        """Request to provide azimuth and elevation samples to the AP.

        Request the AP to set the antenna at the position specified by the
        azimuth and elevation parameters at a specified time.

        Parameters
        ==========
        timestamp_azim_elev : PyTango.DevVarDoubleArray
            index 0 = timestamp : KATCP Timestamp
                          The time when the position coordinates should be applied
            index 1 = azim : float
                          Azimuth coordinate (degrees)
            index 2 = elev : float
                          Elevation coordinate (degrees)

        Returns
        =======
        None.

        Throws
        ======
        PyTango.DevFailed: If ACU control mode is not remote.
        """
        command_name = "Track_Az_El()"
        if self.ap_model.in_remote_control():
            timestamp, azim, elev = timestamp_azim_elev
            self.ap_model.set_az_el(timestamp, azim, elev)
            MODULE_LOGGER.info("Command '{}' executed successfully".format(command_name))
        else:
            Except.throw_exception(self.COMMAND_ERROR_REASON, "Fail, Antenna is not "
                                   "in remote control.", command_name,
                                    ErrSeverity.WARN)

# Unimplemented commands where added just for testing the command list population

    @command
    def Enable_Motion_Profiler(self):
        #TODO Implement if required
        pass

    @command
    def Enable_Point_Error_Systematic(self):
        #TODO Implement if required
        pass

    @command
    def Enable_Point_Error_Tiltmeter(self):
        #TODO Implement if required
        pass

    @command
    def Enable_Warning_Horn(self):
        #TODO Implement if required
        pass

    @command
    def Halt(self):
        #TODO Implement if required
        pass

    @command
    def Help(self):
        #TODO Implement if required
        pass

    @command()
    def Log_Level(self):
        #TODO Implement if required
        pass

    @command
    def Restart(self):
        #TODO Implement if required
        pass

    @command
    def Set_Average_Tilt_An0(self):
        #TODO Implement if required
        pass

    @command
    def Set_Average_Tilt_Aw0(self):
        #TODO Implement if required
        pass

    @command
    def Sensor_List(self):
        #TODO Implement if required
        pass

    @command
    def Sensor_Sampling(self):
        #TODO Implement if required
        pass

    @command
    def Sensor_Value(self):
        #TODO Implement if required
        pass

    @command
    def Set_Stow_Time_Period(self):
        #TODO Implement if required
        pass

    @command
    def Set_Weather_Data(self):
        #TODO Implement if required
        pass

    @command
    def Star_Track(self):
        #TODO Implement if required
        pass

    @command
    def Version_List(self):
        #TODO Implement if required
        pass

    @command
    def Watchdog(self):
        #TODO Implement if required
        pass



def formatter(sensor_name):
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

def unformatter(attr_name):
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


if __name__ == "__main__":
         logging.basicConfig(level=logging.DEBUG)
         server_run([MkatAntennaPositioner])
