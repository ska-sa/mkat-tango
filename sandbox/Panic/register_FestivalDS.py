import PyTango
import subprocess

db = PyTango.Database()

def add_new_device(server,klass,device):
    dev_info = PyTango.DbDevInfo()
    dev_info.name = device
    dev_info.klass = klass
    dev_info.server = server
    db.add_device(dev_info)

# Create a PyAlarm device
add_new_device('FestivalDS/kataware','FestivalDS','mkat/festival/kataware')

print("Succefully registered FestivalDS in Tango-DB")
print("==========================================")
