from __future__ import absolute_import, division, print_function



import PyTango

from future import standard_library

standard_library.install_aliases()

dev_info = PyTango.DbDevInfo()
dev_info.server = "AntennaPositioner/test"
dev_info._class = "AntennaPositioner"
dev_info.name = "test/antenna_positioner/1"
db = PyTango.Database()
db.add_device(dev_info)
print("Registration Successful")
