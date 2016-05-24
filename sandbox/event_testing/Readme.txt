I'm trying to use a file database to run isolated unit tests. This is
essentially what https://github.com/vxgmichel/pytango-devicetest does behind the
scenes. The documentation from pytango-devicetest claims that:

Tango events are not supported by the --file execution mode. See the Tango
documentation for further information.

However, the Tango documentation says:

D.5.2 For release 8 and above

A new event system has been implemented starting with Tango release 8. With this
new event system, the CORBA Notification service is not needed any more. This
means that as soon as all clients using events from devices embedded in the
device server use Tango 8, it is not required to start any process other than
the device server and its clients.

Unfortunately, it seems that in practice the pytango-devicetest readme seems to
be accurate in spite of what the tango documentation says. It seems that events
don't work when a file database is used. 

I'm not sure if I'm doing anything wrong, so I placed a minimal testcase in this
gist: https://gist.github.com/brickZA/8d411ce21aefc688a3cc70a08592c7dc

build info:

python -c "from PyTango.utils import info; print(info())"

PyTango 9.2.0 (9, 2, 0, 'b', 1)
PyTango compiled with:
    Python : 2.7.6
    Numpy  : 0.0.0
    Tango  : 9.2.2
    Boost  : 1.55.0

PyTango runtime is:
    Python : 2.7.6
    Numpy  : None
    Tango  : 9.2.2
    Boost  : 0.0.0

PyTango running on:
('Linux', 'tango-test', '4.2.0-30-generic', '#36-Ubuntu SMP Fri Feb 26 00:58:07 UTC 2016', 'x86_64', 'x86_64')   

Additional details: Built PyTango from pytango9 branch from github, and used
self-made tango .debs that were ported from the current debian packages to build
on Ubuntu 14.04.


Using the database we run the server as:

    python PolledDS.py  --register test/withdb/polled
    python PolledDS.py polled

and client as:

    python PolledDS_client.py 'test/withdb/polled'


This results in a regular stream of event updates:

event_type: change val: True  time: 1462459184.51437 received_time: 1462459184.88911
event_type: periodic val: True  time: 1462459184.51437 received_time: 1462459184.92293
event_type: periodic val: True  time: 1462459185.51359 received_time: 1462459185.51384
event_type: periodic val: True  time: 1462459186.51388 received_time: 1462459186.51412
event_type: periodic val: True  time: 1462459187.51414 received_time: 1462459187.51431
event_type: periodic val: True  time: 1462459188.51441 received_time: 1462459188.51461
event_type: periodic val: True  time: 1462459189.51402 received_time: 1462459189.51462



Running with a file database, we run the server as:

    python PolledDS.py polled -ORBendPoint giop:tcp::12345 -file=tango.db

and client as:

    python PolledDS_client.py 'localhost:12345/test/nodb/polled#dbase=no'

Then we get the initial event update, but after that, only:

2016-05-05 14:37:53,806 - root - ERROR - PolledDS_client - PolledDS_client.py : 36 - Exception while handling event, event_data: EventData[
     attr_name = 'tango://localhost:12345/test/nodb/polled/scalarbool#dbase=no'
    attr_value = None
        device = Polled(test/nodb/polled)
           err = True
        errors = (DevError(desc = 'Event channel is not responding anymore, maybe the server or event system is down', origin = 'EventConsumer::KeepAliveThread()', reason = 'API_EventTimeout', severity = PyTango._PyTango.ErrSeverity.ERR),)
         event = 'change'
reception_date = TimeVal(tv_nsec = 0, tv_sec = 1462459073, tv_usec = 804448)]
Traceback (most recent call last):
  File "PolledDS_client.py", line 29, in printer
    value = attr_value.value
AttributeError: 'NoneType' object has no attribute 'value'
event_type: idl5_change val: True  time: 1462459073.60559 received_time: 1462459073.80705
2016-05-05 14:37:53,807 - root - ERROR - PolledDS_client - PolledDS_client.py : 36 - Exception while handling event, event_data: EventData[
     attr_name = 'tango://localhost:12345/test/nodb/polled/scalarbool#dbase=no'
    attr_value = None
        device = Polled(test/nodb/polled)
           err = True
        errors = (DevError(desc = 'Event channel is not responding anymore, maybe the server or event system is down', origin = 'EventConsumer::KeepAliveThread()', reason = 'API_EventTimeout', severity = PyTango._PyTango.ErrSeverity.ERR),)
         event = 'periodic'
reception_date = TimeVal(tv_nsec = 0, tv_sec = 1462459073, tv_usec = 807174)]
Traceback (most recent call last):
  File "PolledDS_client.py", line 29, in printer
    value = attr_value.value
AttributeError: 'NoneType' object has no attribute 'value'
2016-05-05 14:38:03,813 - root - ERROR - PolledDS_client - PolledDS_client.py : 36 - Exception while handling event, event_data: EventData[
     attr_name = 'tango://localhost:12345/test/nodb/polled/scalarbool#dbase=no'
    attr_value = None
        device = Polled(test/nodb/polled)
           err = True
        errors = (DevError(desc = 'Event channel is not responding anymore, maybe the server or event system is down', origin = 'EventConsumer::KeepAliveThread()', reason = 'API_EventTimeout', severity = PyTango._PyTango.ErrSeverity.ERR),)
         event = 'change'
reception_date = TimeVal(tv_nsec = 0, tv_sec = 1462459083, tv_usec = 813407)]
Traceback (most recent call last):
  File "PolledDS_client.py", line 29, in printer
    value = attr_value.value
AttributeError: 'NoneType' object has no attribute 'value'
event_type: idl5_change val: True  time: 1462459083.60535 received_time: 1462459083.81440
2016-05-05 14:38:03,814 - root - ERROR - PolledDS_client - PolledDS_client.py : 36 - Exception while handling event, event_data: EventData[
     attr_name = 'tango://localhost:12345/test/nodb/polled/scalarbool#dbase=no'
    attr_value = None
        device = Polled(test/nodb/polled)
           err = True
        errors = (DevError(desc = 'Event channel is not responding anymore, maybe the server or event system is down', origin = 'EventConsumer::KeepAliveThread()', reason = 'API_EventTimeout', severity = PyTango._PyTango.ErrSeverity.ERR),)
         event = 'periodic'
reception_date = TimeVal(tv_nsec = 0, tv_sec = 1462459083, tv_usec = 814496)]
Traceback (most recent call last):
  File "PolledDS_client.py", line 29, in printer
    value = attr_value.value
AttributeError: 'NoneType' object has no attribute 'value'
