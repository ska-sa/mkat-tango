from __future__ import absolute_import, division, print_function
from future import standard_library
standard_library.install_aliases()  # noqa: E402

import PyTango
import subprocess

db = PyTango.Database()


def add_new_device(server, klass, device):
    dev_info = PyTango.DbDevInfo()
    dev_info.name = device
    dev_info.klass = klass
    dev_info.server = server
    db.add_device(dev_info)


# Create a PyAlarm device
add_new_device("PyAlarm/kataware", "PyAlarm", "mkat/panic/kataware")

print("Succefully registered PyAlarms in Tango-DB")
print("==========================================")
print("Attempting to run PyAlarm Device Server...")
subprocess.check_call(["PyAlarm", "kataware"])
