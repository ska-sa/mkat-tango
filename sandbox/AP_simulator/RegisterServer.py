from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
import PyTango

dev_info = PyTango.DbDevInfo()
dev_info.server = "AntennaPositioner/test"
dev_info._class = "AntennaPositioner"
dev_info.name = "test/antenna_positioner/1"
db = PyTango.Database()
db.add_device(dev_info)
print("Registration Successful")
