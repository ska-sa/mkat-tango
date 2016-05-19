# mkat-tango
Work relating to the use of tango in MeerKAT and for SKA

The basic idea of the Tango Device Server Object Model (TDSOM) is to treat each device as an object. 
Each device is a separate entity which has its own data and behavior. Each device has a unique name 
which identifies it in network name space. Devices are organized according to classes, each device 
belonging to a class. All classes are derived from one root class thus allowing some common behavior 
for all devices. Four kind of requests can be sent to a device (locally i.e. in the same process, or 
remotely i.e. across the network) :
• Execute actions via commands
• Read/Set data specific to each device belonging to a class via TANGO attributes
• Read/Set data specific to each device belonging to a class via TANGO pipes

NB: Each device is stored in a process called a device server. Devices are configured at runtime via properties
which are stored in a database.
