from __future__ import division, print_function, absolute_import

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
        "AGG_System_Fire_Ok:(mkat/proxies/anc/bms_kapb_fire_active.value " "== True)",
        "AGG_System_Power_Ok:(mkat/proxies/anc/bms_imminent_power_failure " "== True)",
        "AGG_Wind_Speed_reporting:(mkat/proxies/anc/weather_connected == False "
        "or mkat/proxies/anc/weather_state != 'synced' "
        "or mkat/proxies/anc/wind_connected != True "
        "or mkat/proxies/anc/wind_state != 'synced')",
    ]
}
alarm_descriptions = {
    "AlarmDescriptions": [
        "ANC_Wind_Speed:ANC implements this sensor giving 10-min "
        "mean wind speed over all wind sensors",
        "ANC_Wind_Gust:ANC implements this sensor giving highest "
        "gust over all wind sensors",
        "AGG_System_Fire_Ok:True if there is no fire detected " "in KAPB",
        "AGG_System_Power_Ok:True if there is no power supply " "voltage in the KAPB",
        "AGG_Wind_Speed_reporting:True if all wind related sensors ok",
    ]
}
alarm_receivers = {
    "AlarmReceivers": [
        "ANC_Wind_Speed:cam@ska.ac.za",
        "ANC_Wind_Gust:cam@ska.ac.za",
        "AGG_System_Fire_Ok:cam@ska.ac.za",
        "AGG_System_Power_Ok:cam@ska.ac.za",
        "AGG_Wind_Speed_reporting:cam@ska.ac.za",
    ]
}
alarm_severities = {
    "AlarmSeverities": [
        "ANC_Wind_Speed:ALARM",
        "ANC_Wind_Gust:ALARM",
        "AGG_System_Fire_Ok:ALARM",
        "AGG_System_Power_Ok:ALARM",
        "AGG_Wind_Speed_reporting:ALARM",
    ]
}
log_file = {"LogFile": ["/tmp/panic_kataware.log"]}
polling_period = {"PollingPeriod": [1.0]}

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
