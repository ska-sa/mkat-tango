#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################


import time
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
        self.orig_attr_names_map = self.attr_case_insenstive_patch()

    def attr_case_insenstive_patch(self):
        """ Maps the lowercase-converted attribute names to their original
        attribute names.
        Related to the bug reported on the TANGO forum:
        http://www.tango-controls.org/community/forums/post/1468/

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

        commands : dict
            Command name as keys, value is instance of :class:`PyTango.CommandInfo`
            (the return value of :meth:`PyTango.DeviceProxy.command_list_query`)
            for each command.

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

        # A work around to remove the suffix "#dbase=no" string when using a
        # file as a database. Also handle the issue with the attribute name being
        # converted to lowercase in subsequent callbacks.
        if not tango_event_data.err:
            name_trimmed = name.split('#')[0]
            attr_name = self.orig_attr_names_map[name_trimmed.lower()]
            self.sample_event_callback(attr_name, received_timestamp,
                                       timestamp, value, quality, event_type)
        else:
            # TODO KM needs to handle errors accordingly
            MODULE_LOGGER.info("Unhandled DevError(s) occured!!!")

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
        poll_period = 1000      # in milliseconds
        retry_time = 0.5        # in seconds
        retries = 2             # Maximum number of retries

        for attr_name in self.device_attributes:
            if not dp.is_attribute_polled(attr_name):
                _retries = 0
                retry = True
                while retry and _retries < retries:
                    try:
                        dp.poll_attribute(attr_name, poll_period)
                    except PyTango.CommunicationFailed:
                        _retries += 1
                        time.sleep(retry_time)
                    else:
                        retry = False

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
