import logging
import time

LOGGER = logging.getLogger(__name__)

def set_attributes_polling(test_case, device_proxy, device_server, poll_periods):
    """Set attribute polling and restore after test

    Parameters
    ----------

    test_case : unittest.TestCase instance
    device_proxy : PyTango.DeviceProxy instance
    device_server : PyTango.Device instance
        The instance of the device class `device_proxy` is talking to
    poll_periods : dict {"attribute_name" : poll_period}
        `poll_poriod` in milliseconds as per Tango APIs, 0 or falsy to disable
        polling.

    Return value
    ------------

    restore_polling : function
        This function can be used to restore polling if it is to happen before the end of
        the test. Should be idempotent if only one set_attributes_polling() is called per
        test.
    """
    # TODO (NM 2016-04-11) check if this is still needed after upgrade to Tango 9.x For
    # some reason it only works if the device_proxy is used to set polling, but the
    # device_server is used to clear the polling. If polling is cleared using device_proxy
    # it seem to be impossible to restore the polling afterwards.
    attributes = poll_periods.keys()
    initial_polling = {attr: device_proxy.get_attribute_poll_period(attr)
                       for attr in attributes}

    for attr in attributes:
        initial_period = initial_polling[attr]
        new_period = poll_periods[attr]
        # Disable polling for attributes with poll_period of zero / falsy
        # zero initial_period implies no polling currently configed
        if not new_period and initial_period != 0:
            device_server.stop_poll_attribute(attr)
        else:
            # Set the polling
            device_proxy.poll_attribute(attr, new_period)

    def restore_polling():
        retry_time = 0.5
        for attr, period in initial_polling.items():
            if period == 0:
                continue            # zero period implies no polling, nothing to do
            try:
                device_proxy.poll_attribute(attr, period)
                # TODO (NM 2016-04-11) For some reason Tango doesn't seem to handle
                # back-to-back calls, and even with the sleep it sometimes goes bad. Need
                # to check if this is fixed (and core dumps) when we upgrade to Tango 9.x
                time.sleep(0.05)
            except Exception:
                retry = True
                LOGGER.warning('retrying restore of attribute {} in {} due to unhandled'
                               'exception in poll_attribute command'
                               .format(attr, retry_time), exc_info=True)
            else:
                retry = False

            if retry:
                time.sleep(retry_time)
                device_proxy.poll_attribute(attr, period)

    test_case.addCleanup(restore_polling)
    return restore_polling

def disable_attributes_polling(test_case, device_proxy, device_server, attributes):
    """Disable polling for a tango device server, en re-eable at end of test"""
    new_periods = {attr: 0 for attr in attributes}
    return set_attributes_polling(
        test_case, device_proxy, device_server, new_periods)
