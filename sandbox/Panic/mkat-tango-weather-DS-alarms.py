from __future__ import division, print_function, absolute_import

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
    formula=("(mkat_sim/weather/1/temperature<-9.0 or"
             " mkat_sim/weather/1/temperature>50.0)"),
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
