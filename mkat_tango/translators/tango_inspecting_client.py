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
        self.orig_attr_names_map = {}

    def inspect(self):
        """Inspect the tango device for available attributes / commands

        Updates the `device_attributes` and `device_commands` instance attributes

        """
        self.device_attributes = self.inspect_attributes()
        self.device_commands = self.inspect_commands()
        self._dirty = False     # TODO need to consider race conditions
        self.orig_attr_names_map = self.nodb_event_test_patch()

    def nodb_event_test_patch(self):
        """ Maps the lowercase-converted attribute names to their original
        attribute names.
        
        Return Value
        ============

        attributes : dict
            lowercase attribute names as keys, value is the original attribute
            name
            
        """
        return {attr_name.lower(): attr_name 
                for attr_name in self.tango_dp.get_attribute_list()}
        
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
        # TODO NM 2016-04-06 Call a different callback for non-sample events,
        # i.e. error callbacks etc.
        event_type = tango_event_data.event
        attr_value = tango_event_data.attr_value
        name = getattr(attr_value, 'name', None)
        value = getattr(attr_value, 'value', None)
        quality = getattr(attr_value, 'quality', None)
        timestamp = (attr_value.time.totime()
                     if hasattr(attr_value, 'time') else None)

        received_timestamp = tango_event_data.reception_date.totime()
      
        # A work around to remove the suffix "#dbase=no" string and handle 
        # the issue with the attribute name being converted to lowercase
        # in subsequent callbacks when using a file as a database.
        if self.tango_dp.get_device_db() == None:        
            if attr_value != None:
                name_trimmed = name.split('#')
                name_trimmed = self.orig_attr_names_map[name_trimmed[0].lower()]
                self.sample_event_callback(name_trimmed, received_timestamp,
                                           timestamp, value, quality, event_type)
            else:
                MODULE_LOGGER.debug("Issues with Tango DevUChar data type")
        else:
            self.sample_event_callback(name, received_timestamp, timestamp,
                                   value, quality, event_type)
        

    def sample_event_callback(
            self, name, received_timestamp, timestamp, value, quality,
            event_type):
        """Callback called for every sample event. NOP implementation.

        Intended for subclasses to override this method, or for the method to be
        replaced in instances

        Parameters

        """
        pass

    def setup_attribute_sampling(self, periodic=True, change=True, archive=True,
                                 data_ready=False, user=True):
        """Subscribe to all or some types of Tango attribute events"""
        dp = self.tango_dp
        for attr_name in self.device_attributes:
            try:
                subs = lambda etype: dp.subscribe_event(
                    attr_name, etype, self.tango_event_handler)
                # TODO NM Need an individual try-except around each of these
                if periodic:
                    self._event_ids.add(subs(PyTango.EventType.PERIODIC_EVENT))
                if change:
                    self._event_ids.add(subs(PyTango.EventType.CHANGE_EVENT))
                if archive:
                    self._event_ids.add(subs(PyTango.EventType.ARCHIVE_EVENT))
                if data_ready:
                    self._event_ids.add(subs(PyTango.EventType.DATA_READY_EVENT))
                if user:
                    self._event_ids.add(subs(PyTango.EventType.USER_EVENT))
            except PyTango.DevFailed, exc:
                exc_reasons = set([arg.reason for arg in exc.args])
                if 'API_AttributePollingNotStarted' in exc_reasons:
                    MODULE_LOGGER.warn('TODO NM: Need to implement something for '
                                       'attributes that are not polled, processing '
                                       'attribute {}'.format(attr_name))
                elif 'API_EventPropertiesNotSet' in exc_reasons:
                    MODULE_LOGGER.info('Attribute {} has no event properties set'
                                       .format(attr_name))
                else:
                    raise

    def clear_attribute_sampling(self):
        """Unsubscribe from all Tango events previously subscribed to

        Cleanup for setup_attribute_sampling

        """
        while self._event_ids:
            ev_id = self._event_ids.pop()
            self.tango_dp.unsubscribe_event(ev_id)
