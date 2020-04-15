from __future__ import division, print_function, absolute_import

import PyTango

ap_name = "mkat_sim/ap/1"

dev_info = PyTango.DbDevInfo()
dev_info.server = "mkat-tango-AP-DS/test"
dev_info._class = "MkatAntennaPositioner"
dev_info.name = ap_name
db = PyTango.Database()
db.add_device(dev_info)
print("Registration of antenna positioner Successful")
