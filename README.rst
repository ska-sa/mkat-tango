.. _license: https://github.com/ska-sa/mkat-tango/blob/master/LICENSE

=============================================
MeerKAT Tango integration and experimentation
=============================================

Work relating to the use of tango in MeerKAT (MKAT) and for SKA. This package contains:

simulators
  Simulators of "real" telescope devices with TANGO interfaces. They can be used
  to test a telescope control system in a simulated environment without having
  to use any "real" hardware.

translators
  Components that allow bidrectional communications between KATCP and TANGO
  based control systems. Also provides some helper utilities for integrating
  TANGO components into the MKAT system.



Simulators
==========

Weather simulator
-----------------

The weather simulator is built using tango_simlib_ . It provides the
tango `Weather` device class. The weather simulator's behaviour can be modified
by attaching a standard `SimControl` class to it. The `SimControl` class must
run in the same device server instance as the `Weather` class. The `SimControl`
class finds the `Weather` instance by getting its name from the `model_key`
property. Most of the weather simulator attributes are implemented as
`GaussianSlewRateLimited` quantities.

Example of starting a weather simulator with a SimControl instance using
tango_launcher ::

  mkat-tango-tango_launcher --name mkat_sim/weather/2 --class Weather\
                          --name mkat_simcontrol/weather/2 --class SimControl\ 
                          --server-command mkat-tango-weather-DS --port 0\
                          --server-instance tango-launched\
  --put-device-property  mkat_simcontrol/weather/2:model_key:mkat_sim/weather/2


.. _tango_simlib: https://github.com/ska-sa/tango-simlib


MKAT TANGO AP simulator
--------------------------

The actual MKAT antenna positioner (AP) devices have KATCP interfaces. To aid
testing and development of the MKAT CAM (i.e TM) system, a fairly detailed 
simulator that mimics the MKAT AP behaviour and exposes a TANGO 
interface was developed.


Translators
===========

tangodevice2katcp
-----------------

Allows a KATCP client to talk to a TANGO device. Translates TANGO commands to
KATCP requests and TANGO attributes to KATCP sensors. Subscribes to all
attribute events and sets up polling if neccesary.

Example of launching a translator that connects as client to the Tango device
`mkat_sim/weather/1` and exposes it as a KATCP device server listening on TCP
port 2051 ::

  mkat-tango-tangodevice2katcp --katcp-server-address :2051 mkat_sim/weather/1

Types
^^^^^

KATCP and TANGO both have defined data types, but the KATCP protocol (being text
based) has less strict definitions. E.g. KATCP only defines a singular integer
type with no specific bounds, while TANGO distinguishes between signed and
unsigned, and between 8, 16, 32 or 64-bit integers. The KATCP library does,
however, provide features for enforcing bounds and other checks on typed
quantities, and these are used to enforce the appropriate bounds. E.g. if the
TANGO device exposes a command that takes an 8-bit unsigned integer parameter, the
KATCP translator will enforce the corresponding KATCP parameter to have a value
of between 0 and 255.


Limitations
^^^^^^^^^^^

 Easily removable limitations:

 - Does not handle TANGO commands that take or return arrayed values.

 More difficult limitations:

 - Does not support IMAGE attributes. KATCP does not define how sensors with 2-D arrayed
   values should be handled.
  
 Note: 
     For SPECTRUM attributes, the 1-D array is decomposed into individual 
     KATCP sensors and the indices are appended to the end of the names of the generated 
     sensors e.g. test.0, test.1 etc.


katcpdevice2tango
-----------------

Allows a TANGO client to talk to a KATCP device. Currently only translates KATCP
sensors to TANGO attributes. Sets up `event` strategies on all KATCP sensors so
that all updates are received. The KATCP server is located by reading the TANGO
device property `katcp_address`.

Example of launching a translator that connects as client to the KATCP device
running on host `localhost`, TCP port 5000 and exposing it as a TANGO device
named `katcp/basic/1` ::

  mkat-tango-tango_launcher --name katcp/basic/1 --class TangoDeviceServer\
  --server-command mkat-tango-katcpdevice2tango-DS --server-instance basic\
  --port 0 --put-device-property katcp/basic/1:katcp_address:localhost:5000

If `katcp/basic/` is already registered in the tango DB (class:
TangoDeviceServer, device server mkat-tango-katcpdevice2tango-DS, property
`katcp_address` = `localhost:5000`, server instance: `basic`) ::

  mkat-tango-katcpdevice2tango-DS basic
  


tango_launcher
--------------

A helper script (`mkat-tango-tango_launcher`) is provided for registering,
setting device properties, and starting a TANGO device server in a single
step. This is useful when starting a TANGO device in the MKAT system, since
the MKAT system has no direct understanding of the TANGO database and manages
system interconnections through command-line parameters when starting various
telescope processes. MKAT also has its own TCP port allocation method, which
could conflict with the TANGO system's automatic port allocation. For this
reason `mkat-tango-tango_launcher` requires a `--port` flag to be passed,
controlling the TCP port where the TANGO device server will listen.  To use the
standard TANGO port allocation, use `--port 0`.

Run `mkat-tango-tango_launcher --help` for more information, or see examples in
the sections above.

Notes on running tests
======================

TANGO segfaults when restarting a device main function
------------------------------------------------------

PyTango segfaults if a device server is started more than once in a single
process. This means that it is not possible to start/stop a tango device server
as part of a test fixture. To work around this, the nose process plugin along
with the `tango.test_context` module is used. Adding
`--processes=1 --process-restartworker --process-timeout=300` to a nose command
line will cause each test tango device class (tango device fixtures are handled
per-class) to be run in a new process.

Events and Polling
------------------

To run tests speedily, it is useful to have attributes refresh as quickly as
possible, hence the polling period is set faster than usual. It was noted that
when polling at a period of less than 50 ms, updates become
inconsistent. I.e. the observed time difference between updates fluctuates
(50+-20 ms), and sometime updates are skipped.

Periodic event type
  An event is sent at a fixed periodic interval. The frequency of this event is
  determined by the `event_period` property of the attribute and the polling
  frequency. The polling frequency determines the highest frequency at which the
  attribute is read. This `event_period` determines the highest frequency at which
  the periodic, or any other, event is sent.

Docker images for development and testing
=========================================

Introduction
------------

Docker containers are useful for developing mkat-tango locally due its package requirements. This
provides the information on how to , and the Docker images provide a
similar environment to that used by Jenkins for the Continuous
Integration tests.

Building the Docker image
-------------------------

Run commands like the following:

``docker build -t mkat-tango .``

Access a bash shell inside the docker container
-----------------------------------------------

``docker run -ti mkat-tango '/bin/bash'``

Using a container with an IDE
-----------------------------

Once the image has been built, it can be used with IDEs like
`PyCharm <https://www.jetbrains.com/help/pycharm/using-docker-as-a-remote-interpreter.html#config-docker>`__
(Professional version only)

PyCharm(with Dockerfile):
-------------------------

Add a new interpreter:
   - Open the *Add Interpreter...* dialog
   - Select *Docker*
   - Pick the image to use, e.g., ``mkat-tango:mkat-tango``
   - Select python interpreter ``python2`` or ``python3``

PyCharm(with docker-compose):
-----------------------------

Add a new interpreter:
    - Open the *Add Interpreter...* dialog
    - Select *Docker Compose*
    - Pick the service to use, e.g., ``mkat-tango``
    - Select python interpreter ``python2`` or ``python3``

Running tests:
  - If you want to run all the tests inside bash take a look at the JenkinsFile for an example of how it is executed.

License
=======

This project is licensed under the BSD 3-Clause License - see license_ for details.