from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

import sys
import time
import logging

import PyTango


logger = logging.getLogger()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(module)s - "
    "%(pathname)s : %(lineno)d - %(message)s",
    level=logging.INFO,
)


device_name = sys.argv[1]

td = PyTango.DeviceProxy(device_name)
attr_name = "ScalarBool"


# Set up a listener
def printer(event_data):
    # print event_data # Seems to be an PyTango.EventData instance
    try:
        event_type = event_data.event
        attr_value = event_data.attr_value
        value = attr_value.value
        name = attr_value.name
        timestamp = attr_value.time.totime()
        received_timestamp = event_data.reception_date.totime()
        print(
            "event_type: {} name: {} val: {}  time: {:.5f} received_time: {:.5f}".format(
                event_type, name, value, timestamp, received_timestamp
            )
        )
    except Exception:
        logger.exception(
            "Exception while handling event, event_data: {}".format(event_data)
        )


event_ids = {
    "change": td.subscribe_event(attr_name, PyTango.EventType.CHANGE_EVENT, printer),
    "periodic": td.subscribe_event(attr_name, PyTango.EventType.PERIODIC_EVENT, printer),
}


time.sleep(1000)
