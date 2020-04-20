from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import *
import PyTango

weather_name = "mkat_sim/weather/1"
weather_simcontrol_name = "mkat_simcontrol/weather/1"

dev_info = PyTango.DbDevInfo()
dev_info.server = "mkat-tango-weather-DS/test"
dev_info._class = "Weather"
dev_info.name = weather_name
db = PyTango.Database()
db.add_device(dev_info)
print("Registration of weather Successful")

dev_info = PyTango.DbDevInfo()
dev_info.server = "mkat-tango-weather-DS/test"
dev_info._class = "SimControl"
dev_info.name = weather_simcontrol_name
db = PyTango.Database()
db.add_device(dev_info)
print("Registration of weather control Successful")

db.put_device_property(weather_simcontrol_name, dict(model_key=[weather_name]))
