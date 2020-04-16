from __future__ import absolute_import, print_function, division

import panic

alarms = panic.api()

alarms.add(
    "ANC_Wind_Gust",
    "mkat/panic/kataware",
    formula=(
        "(mkat/proxies/anc/gust_wind_speed.value > 16.9 or"
        " mkat/proxies/anc/gust_wind_speed.value < 1.5)"
    ),
    description="ANC implements this sensor giving highest gust over all wind sensors",
    receivers="cam@ska.ac.za, ACTION(alarm:command:mkat/proxies/m0*/set_windstow)",
)
alarms.add(
    "ANC_Wind_Speed",
    "mkat/panic/kataware",
    formula=(
        "(mkat/proxies/anc/mean_wind_speed.value > 11.1 or"
        " mkat/proxies/anc/mean_wind_speed.value < 1.5)"
    ),
    description=(
        "ANC implements this sensor giving 10-min mean "
        "wind speed over all wind sensors"
    ),
    receivers="kmadisa@ska.ac.za",
)
