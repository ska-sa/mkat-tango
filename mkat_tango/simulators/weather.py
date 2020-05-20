#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
MeerKAT weather simulator and weather simulator control.
    @author MeerKAT CAM team <cam@ska.ac.za>
"""
from __future__ import absolute_import, division, print_function
from future import standard_library
standard_library.install_aliases()  # noqa: E402

import logging
import weakref

from functools import partial

from tango import Attr, AttrWriteType
from tango import AttrQuality, DevState, DevLong
from tango import DevString, DevDouble, DevBoolean
from tango import UserDefaultAttrProp
from tango.server import Device
from tango_simlib import main
from tango_simlib import model
from tango_simlib import quantities
from tango_simlib import sim_test_interface

MODULE_LOGGER = logging.getLogger(__name__)

MODULE_LOGGER.debug("Importing")

PYTHON_TYPES_TO_TANGO_TYPE = {
    # Scalar types
    str: DevString,
    int: DevLong,
    float: DevDouble,
    bool: DevBoolean,
}


class Weather(Device):

    instances = weakref.WeakValueDictionary()  # Access instances for debugging
    DEFAULT_POLLING_PERIOD_MS = int(1 * 1000)

    def init_device(self):
        super(Weather, self).init_device()
        name = self.get_name()
        self.instances[name] = self
        self.model = WeatherModel(name)
        self.set_state(DevState.ON)

    def initialize_dynamic_attributes(self):
        """The device method that sets up attributes during run time"""
        model_sim_quants = self.model.sim_quantities
        attribute_list = {attr for attr in list(model_sim_quants.keys())}

        for attribute_name in attribute_list:
            model.MODULE_LOGGER.info(
                "Added dynamic weather {} attribute".format(attribute_name)
            )
            attr_props = UserDefaultAttrProp()
            meta_data = model_sim_quants[attribute_name].meta
            attr_dtype = PYTHON_TYPES_TO_TANGO_TYPE[meta_data.pop("dtype")]
            attr = Attr(attribute_name, attr_dtype, AttrWriteType.READ)
            for prop in list(meta_data.keys()):
                attr_prop = getattr(attr_props, "set_" + prop)
                if attr_prop:
                    attr_prop(str(meta_data[prop]))
            attr.set_default_properties(attr_props)
            self.add_attribute(attr, self.read_attributes)

    def always_executed_hook(self):
        self.model.update()

    def read_attributes(self, attr):
        """Method reading an attribute value

        Arguments
        ==========

        attr : tango.DevAttr
            The attribute to read from.

        """
        name = attr.get_name()
        value, update_time = self.model.quantity_state[name]
        quality = AttrQuality.ATTR_VALID
        self.info_stream("Reading attribute %s", name)
        attr.set_value_date_quality(value, update_time, quality)


class WeatherModel(model.Model):
    def setup_sim_quantities(self):
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time
        )
        ConstantQuantity = partial(quantities.ConstantQuantity, start_time=start_time)
        self.sim_quantities.update(
            {
                "temperature": GaussianSlewLimited(
                    mean=20,
                    std_dev=20,
                    max_slew_rate=5,
                    min_bound=-10,
                    max_bound=55,
                    meta={
                        "label": "Outside Temperature",
                        "dtype": float,
                        "description": "Current temperature outside near the telescope.",
                        "min_warning": -5,
                        "max_warning": 45,
                        "min_alarm": -9,
                        "max_alarm": 50,
                        "min_value": -10,
                        "max_value": 51,
                        "unit": "Degrees Centrigrade",
                        "period": Weather.DEFAULT_POLLING_PERIOD_MS,
                    },
                ),
                "insolation": GaussianSlewLimited(
                    mean=500,
                    std_dev=1000,
                    max_slew_rate=100,
                    min_bound=0,
                    max_bound=1100,
                    meta={
                        "label": "Insolation",
                        "dtype": float,
                        "description": "Sun intensity in central telescope area.",
                        "max_warning": 1000,
                        "max_alarm": 1100,
                        "max_value": 1200,
                        "min_value": 0,
                        "unit": "W/m^2",
                        "period": Weather.DEFAULT_POLLING_PERIOD_MS,
                    },
                ),
                "pressure": GaussianSlewLimited(
                    mean=650,
                    std_dev=100,
                    max_slew_rate=50,
                    min_bound=350,
                    max_bound=1500,
                    meta={
                        "label": "Barometric pressure",
                        "dtype": float,
                        "description": "Barometric pressure in central telescope area.",
                        "max_warning": 900,
                        "max_alarm": 1000,
                        "max_value": 1100,
                        "min_value": 500,
                        "unit": "mbar",
                        "period": Weather.DEFAULT_POLLING_PERIOD_MS,
                    },
                ),
                "rainfall": GaussianSlewLimited(
                    mean=1.5,
                    std_dev=0.5,
                    max_slew_rate=0.1,
                    min_bound=0,
                    max_bound=5,
                    meta={
                        "label": "Rainfall",
                        "dtype": float,
                        "description": "Rainfall in central telescope area.",
                        "max_warning": 3.0,
                        "max_alarm": 3.1,
                        "max_value": 3.2,
                        "min_value": 0,
                        "unit": "mm",
                        "period": Weather.DEFAULT_POLLING_PERIOD_MS,
                    },
                ),
            }
        )
        self.sim_quantities["relative-humidity"] = GaussianSlewLimited(
            mean=65,
            std_dev=10,
            max_slew_rate=10,
            min_bound=0,
            max_bound=150,
            meta={
                "label": "Air humidity",
                "dtype": float,
                "description": "Relative humidity in central telescope area.",
                "max_warning": 98,
                "max_alarm": 99,
                "max_value": 100,
                "min_value": 0,
                "unit": "percent",
                "period": Weather.DEFAULT_POLLING_PERIOD_MS,
            },
        )
        self.sim_quantities["wind-speed"] = GaussianSlewLimited(
            mean=1,
            std_dev=20,
            max_slew_rate=3,
            min_bound=0,
            max_bound=100,
            meta={
                "label": "Wind speed",
                "dtype": float,
                "description": "Wind speed in central telescope area.",
                "max_warning": 15,
                "max_alarm": 25,
                "max_value": 30,
                "min_value": 0,
                "unit": "m/s",
                "period": Weather.DEFAULT_POLLING_PERIOD_MS,
            },
        )
        self.sim_quantities["wind-direction"] = GaussianSlewLimited(
            mean=0,
            std_dev=150,
            max_slew_rate=60,
            min_bound=0,
            max_bound=359.9999,
            meta={
                "label": "Wind direction",
                "dtype": float,
                "description": "Wind direction in central telescope area.",
                "max_value": 360,
                "min_value": 0,
                "unit": "Degrees",
                "period": Weather.DEFAULT_POLLING_PERIOD_MS,
            },
        )
        self.sim_quantities["input-comms-ok"] = ConstantQuantity(
            start_value=True,
            meta={
                "label": "Input communication OK",
                "dtype": bool,
                "description": "Communications with all weather sensors are nominal.",
                "period": Weather.DEFAULT_POLLING_PERIOD_MS,
            },
        )
        super(WeatherModel, self).setup_sim_quantities()


weather_main = partial(
    main.simulator_main, Weather, sim_test_interface.TangoTestDeviceServerBase
)

if __name__ == "__main__":
    weather_main()
