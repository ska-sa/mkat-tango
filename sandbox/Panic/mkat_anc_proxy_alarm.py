from __future__ import absolute_import, print_function, division


from future import standard_library
standard_library.install_aliases()
from builtins import *
import PyTango

db = PyTango.Database()

# PyAlarm device server name alarms will be exported to as attributes
pyalarm_name = "mkat/panic/kataware"

# Device properties (Alarm decleration)
# ref: katcamconfig/static/alarms/mkat.sim.conf

alarm_list = {
    "AlarmList": [
        "ANC_Wind_Speed:(mkat/proxies/anc/mean_wind_speed.value > 11.1 or "
        "mkat/proxies/anc/mean_wind_speed.value < 1.5)",
        "ANC_Wind_Gust:(mkat/proxies/anc/gust_wind_speed.value > 16.9 or "
        "mkat/proxies/anc/gust_wind_speed.value < 1.5)",
    ]
}
alarm_descriptions = {
    "AlarmDescriptions": [
        "ANC_Wind_Speed:ANC implements this sensor giving 10-min "
        "mean wind speed over all wind sensors",
        "ANC_Wind_Gust:ANC implements this sensor giving highest "
        "gust over all wind sensors",
    ]
}
alarm_receivers = {
    "AlarmReceivers": [
        "ANC_Wind_Speed:cam@ska.ac.za",
        (
            "ANC_Wind_Gust:cam@ska.ac.za,"
            " ACTION(alarm:command:mkat_sim/mkat_ap_tango/1/Stow)"
        ),
    ]
}
alarm_severities = {"AlarmSeverities": ["ANC_Wind_Speed:ALARM", "ANC_Wind_Gust:ALARM"]}
log_file = {"LogFile": ["/tmp/panic_kataware.log"]}
polling_period = {"PollingPeriod": [5.0]}

# List of required Device properties
properties = [
    alarm_list,
    alarm_descriptions,
    alarm_receivers,
    alarm_severities,
    log_file,
    polling_period,
]

for prop in properties:
    db.put_device_property(pyalarm_name, prop)
