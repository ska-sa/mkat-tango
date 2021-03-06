# create_weatherDS_alarms.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

import panic

alarms = panic.api()

alarms.add(
    "Rainfall",
    "mkat/panic/kataware",
    formula="(mkat_sim/weather/1/rainfall>3.1)",
    description="Rainfall in central telescope area.",
    receivers="kmadisa@ska.ac.za",
)
alarms.add(
    "Outside_Temperature",
    "mkat/panic/kataware",
    formula=(
        "(mkat_sim/weather/1/temperature<-9.0 or" " mkat_sim/weather/1/temperature>50.0)"
    ),
    description="Current temperature outside near the telescope.",
    receivers="kmadisa@ska.ac.za",
)
alarms.add(
    "Wind_speed",
    "mkat/panic/kataware",
    formula="(mkat_sim/weather/1/wind-speed>25.0)",
    description="Wind speed in central telescope area.",
    receivers="kmadisa@ska.ac.za",
)
alarms.add(
    "Barometric_pressure",
    "mkat/panic/kataware",
    formula="(mkat_sim/weather/1/pressure>1000)",
    description="Barometric pressure in central telescope area.",
    receivers="kmadisa@ska.ac.za",
)
alarms.add(
    "Insolation",
    "mkat/panic/kataware",
    formula="(mkat_sim/weather/1/insolation>1100.0)",
    description="Sun intensity in central telescope area.",
    receivers="kmadisa@ska.ac.za",
)
alarms.add(
    "Air_humidity",
    "mkat/panic/kataware",
    formula="(mkat_sim/weather/1/relative-humidity.value>99)",
    description="Relative humidity in central telescope area.",
    receivers="kmadisa@ska.ac.za",
)
