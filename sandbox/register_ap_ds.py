import PyTango

ap_name = "mkat_sim/ap/1"
ap_simcontrol_name = "mkat_simcontrol/ap/1"

dev_info = PyTango.DbDevInfo()
dev_info.server = "mkat-tango-AP-DS/test"
dev_info._class = "MkatAntennaPositioner"
dev_info.name = ap_name
db = PyTango.Database()
db.add_device(dev_info)
print "Registration of antenna positioner Successful"

dev_info = PyTango.DbDevInfo()
dev_info.server = "mkat-tango-AP-DS/test"
dev_info._class = "SimControl"
dev_info.name = ap_simcontrol_name
db = PyTango.Database()
db.add_device(dev_info)
print "Registration of ap control Successful"

db.put_device_property(ap_simcontrol_name, dict(model_key=[ap_name]))
