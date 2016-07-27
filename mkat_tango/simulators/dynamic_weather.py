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
MeerKAT weather simulator and weather simulator control.
    @author MeerKAT CAM team <cam@ska.ac.za>
    """

import time
import weakref
import logging
import collections
import PyTango
import numpy

from functools import partial

from PyTango import UserDefaultAttrProp
from PyTango import AttrQuality, DevState
from PyTango import Attr, AttrWriteType, WAttribute
from PyTango import DevString, DevDouble, DevBoolean
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command

from mkat_tango.simlib import sim_test_interface
from mkat_tango.simlib import quantities
from mkat_tango.simlib import model
from mkat_tango.simlib import main

MODULE_LOGGER = logging.getLogger(__name__)


MODULE_LOGGER.debug('Importing')

class Weather(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary()  # Access instances for debugging
    DEFAULT_POLLING_PERIOD_MS = int(1 * 1000)

    def init_device(self):
        super(Weather, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        self.model = WeatherModel(name)
        self.set_state(DevState.ON)


class WeatherModel(model.Model):

    def setup_sim_quantities(self):
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)
        self.sim_quantities.update(dict(
            temperature=GaussianSlewLimited(
                mean=20, std_dev=20, max_slew_rate=5,
                min_bound=-10, max_bound=55, meta=dict(
                    label="Outside Temperature",
                    dtype=float,
                    doc="Current temperature outside near the telescope",
                    min_warning=-5, max_warning=45,
                    min_alarm=-9, max_alarm=50,
                    min_value=-10, max_value=51,
                    unit="Degrees Centrigrade",
                    polling_period=Weather.DEFAULT_POLLING_PERIOD_MS)),
            insolation=GaussianSlewLimited(
                mean=500, std_dev=1000, max_slew_rate=100,
                min_bound=0, max_bound=1100, meta=dict(
                    label="Insolation",
                    dtype=float,
                    doc="Sun intensity in central telescope area",
                    max_warning=1000, max_alarm=1100,
                    max_value=1200, min_value=0,
                    unit="W/m^2",
                    polling_period=Weather.DEFAULT_POLLING_PERIOD_MS)),
            pressure=GaussianSlewLimited(
                mean=650, std_dev=100, max_slew_rate=50,
                min_bound=350, max_bound=1500, meta=dict(
                    label="Barometric pressure",
                    dtype=float,
                    doc="Barometric pressure in central telescope area",
                    max_warning=900, max_alarm=1000,
                    max_value=1100, min_value=500,
                    unit="mbar",
                    polling_period=Weather.DEFAULT_POLLING_PERIOD_MS)),
            rainfall=GaussianSlewLimited(
                mean=1.5, std_dev=0.5, max_slew_rate=0.1,
                min_bound=0, max_bound=5, meta=dict(
                    label="Rainfall",
                    dtype=float,
                    doc="Rainfall in central telescope area",
                    max_warning=3.0, max_alarm=3.1,
                    max_value=3.2, min_value=0,
                    unit="mm",
                    polling_period=Weather.DEFAULT_POLLING_PERIOD_MS)),
        ))
#        self.sim_quantities['relative-humidity'] = GaussianSlewLimited(
#            mean=65, std_dev=10, max_slew_rate=10,
#            min_bound=0, max_bound=150)
#        self.sim_quantities['wind-speed'] = GaussianSlewLimited(
#                mean=1, std_dev=20, max_slew_rate=3,
#                min_bound=0, max_bound=100)
#        self.sim_quantities['wind-direction'] = GaussianSlewLimited(
#                mean=0, std_dev=150, max_slew_rate=60,
#                min_bound=0, max_bound=359.9999)
#        self.sim_quantities['input-comms-ok'] = ConstantQuantity(start_value=True)
#                dict(label="Wind speed",
#                    dtype=float,
#                    doc="Wind speed in central telescope area",
#                    max_warning=15, max_alarm=25,
#                    max_value=30, min_value=0,
#                    unit="m/s",
#                    polling_period=Weather.DEFAULT_POLLING_PERIOD_MS)],
        super(WeatherModel, self).setup_sim_quantities()


weather_main = partial(main.simulator_main, Weather, sim_test_interface.SimControl)

if __name__ == "__main__":
    weather_main()
