import logging

import PyTango


MODULE_LOGGER = logging.getLogger(__name__)

class TangoInspectingClient(object):
    """Wrapper around a Tango DeviceProxy that tracks commands/attributes

    Caches available commands and attributes in a simple data structure, and can
    systematically set up polling / event listening on all a device's attributes

    Parameters
    ==========

    tango_device_proxy : :class:`PyTango.DeviceProxy` instance.

    """
    def __init__(self, tango_device_proxy):
        self.tango_dp = tango_device_proxy
        self.device_attributes = {}
        self.device_commands = {}
        self._event_ids = set()
        # True if the stored device attributes/commands are potentially outdated
        self._dirty = True

    def inspect(self):
        """Inspect the tango device for available attributes / commands

        Updates the `device_attributes` and `device_commands` instance attributes

        """
        self.device_attributes = self.inspect_attributes()
        self.device_commands = self.inspect_commands()
        self._dirty = False     # TODO need to consider race conditions

    def inspect_attributes(self):
        """Return data structure of tango device attributes

        Return Value
        ============

        attributes : dict
            Attribute names as keys, value is the return value of
            :meth:`PyTango.DeviceProxy.get_attribute_config` of each attribute

        """
        return {attr_name: self.tango_dp.get_attribute_config(attr_name)
                for attr_name in self.tango_dp.get_attribute_list()}

    def inspect_commands(self):
        """Return data structure of tango device commands

        Return Value
        ============

        attributes : dict
            Command name as keys, value is the return value of
            :meth:`PyTango.DeviceProxy.command_list_query` for each command.

        """
        return {cmd_info.cmd_name: cmd_info
                for cmd_info in self.tango_dp.command_list_query()}

    def tango_event_handler(self, tango_event_data):
        """Handles tango event callbacks.

        Extracts neccesary data and calls :meth:`sample_event_callback` with
        said data.

        """
        event_type = tango_event_data.event
        attr_value = tango_event_data.attr_value
        name = attr_value.name
        value = attr_value.value
        quality = attr_value.quality
        timestamp = attr_value.time.totime()
        received_timestamp = tango_event_data.reception_date.totime()

        self.sample_event_callback(name, received_timestamp, timestamp,
                                   value, quality, event_type)


    def sample_event_callback(
            self, name, received_timestamp, timestamp, value, quality,
            event_type):
        """Callback called for every sample event. NOP implementation.

        Intended for subclasses to override this method, or for the method to be
        replace in instances

        """
        pass

    def setup_attribute_sampling(self, periodic=True, change=True, archive=True,
                                 data_ready=True, quality=True, user=True):
        """Subscribe to all or some types of Tango attribute events"""
        dp = self.tango_dp
        for attr_name in self.device_attributes:
            subs = lambda etype: dp.subscribe_event(
                attr_name, etype, self.tango_event_handler)

            if periodic:
                self._event_ids.add(subs(PyTango.EventType.PERIODIC_EVENT))
            if change:
                self._event_ids.add(subs(PyTango.EventType.CHANGE_EVENT))
            if archive:
                self._event_ids.add(subs(PyTango.EventType.ARCHIVE_EVENT))
            if data_ready:
                self._event_ids.add(subs(PyTango.EventType.DATA_READY_EVENT))
            if quality:
                self._event_ids.add(subs(PyTango.EventType.QUALITY_EVENT))
            if user:
                self._event_ids.add(subs(PyTango.EventType.USER_EVENT))

    def clear_attribute_sampling(self):
        """Unsubscribe from all Tango events previously subscribed to

        Cleanup for setup_attribute_sampling

        """
        while self._event_ids:
            ev_id = self._event_ids.pop()
            self.tango_dp.unsubscribe_event(ev_id)
