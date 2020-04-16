from __future__ import absolute_import, print_function, division


from future import standard_library
standard_library.install_aliases()
from builtins import *
import time
import PyTango
import logging
import pylab as pl
import threading

logger = logging.getLogger()


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(module)s - ", level=logging.INFO
)

AP = PyTango.DeviceProxy("test/antenna_positioner/1")

# Set up a listener
def printer(event_data):
    try:
        print(event_data)  # A PyTango.EventData instance
    except Exception:
        logger.exception(
            "Exception while handling event, event_data: {}".format(event_data)
        )


poll_event_az = AP.subscribe_event(
    "actual_azimuth", PyTango.EventType.CHANGE_EVENT, printer
)
poll_event_el = AP.subscribe_event(
    "actual_elevation", PyTango.EventType.CHANGE_EVENT, printer
)


def plotter():
    pl.plot(AP.actual_azimuth, AP.actual_elevation, "o")
    pl.xlabel("actual azimuth")
    pl.ylabel("actual elevation")
    pl.title("el-az AP coordinates")
    pl.xlim(-185.0, 275.0)
    pl.ylim(10.0, 92.0)
    pl.axvspan(-180.0, -185.0, color="y", alpha=0.5, lw=0)
    pl.axvspan(270.0, 275.0, color="y", alpha=0.5, lw=0)
    pl.axhspan(10.0, 15.0, facecolor="y", alpha=0.5)
    pl.axhspan(87.0, 92.0, facecolor="y", alpha=0.5)
    pl.grid()
    pl.ion()
    pl.show()
    while True:
        pl.plot(AP.actual_azimuth, AP.actual_elevation, "o")
        pl.draw()
        time.sleep(0.1)


plotting_thread = threading.Thread(target=plotter)
plotting_thread.setDaemon(True)
plotting_thread.start()
