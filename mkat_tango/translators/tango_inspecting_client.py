###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

from builtins import object
import time
import logging

import tango

from tango import AttrQuality

log = logging.getLogger("mkat_tango.translators.tango_inspecting_client")


class TangoInspectingClient(object):
    """Wrapper around a Tango DeviceProxy that tracks commands/attributes

    Caches available commands and attributes in a simple data structure, and can
    systematically set up polling / event listening on all a device's attributes

    Parameters
    ==========

    tango_device_proxy : :class:`tango.DeviceProxy` instance.

    """

    def __init__(self, tango_device_proxy, logger=log):
        self.tango_dp = tango_device_proxy
        self.device_attributes = {}
        self.device_commands = {}
        self._event_ids = set()
        self._logger = logger
        self.orig_attr_names_map = {}
        self._interface_change_event_id = None

    def __del__(self):
        try:
            self.tango_dp.unsubscribe_event(self._interface_change_event_id)
        except tango.DevFailed as exc:
            exc_reasons = {arg.reason for arg in exc.args}
            if "API_EventNotFound" in exc_reasons:
                self._logger.debug(
                    "No event with id {} was set up.".format(
                        self._interface_change_event_id
                    )
                )
            else:
                raise
        else:
            self._interface_change_event_id = None

    def inspect(self):
        """Inspect the tango device for available attributes / commands

        Updates the `device_attributes` and `device_commands` instance attributes

        """
        self._subscribe_to_event(tango.EventType.INTERFACE_CHANGE_EVENT)
        self.device_attributes = self.inspect_attributes()
        self.device_commands = self.inspect_commands()
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
        return {
            attr_name.lower(): attr_name
            for attr_name in self.tango_dp.get_attribute_list()
        }

    def inspect_attributes(self):
        """Return data structure of tango device attributes

        Return Value
        ============

        attributes : dict
            Attribute names as keys, value is an instance of
            :class: `tango._tango.AttributeInfoEx`, a return value of
            :meth:`tango.DeviceProxy.get_attribute_config` of each attribute.
        """
        return {
            attr_name: self.tango_dp.get_attribute_config(attr_name)
            for attr_name in self.tango_dp.get_attribute_list()
        }

    def inspect_commands(self):
        """Return data structure of tango device commands

        Return Value
        ============

        commands : dict
            Command name as keys, value is instance of :class:`tango.CommandInfo`
            (the return value of :meth:`tango.DeviceProxy.command_list_query`)
            for each command.

        """
        return {
            cmd_info.cmd_name: cmd_info for cmd_info in self.tango_dp.command_list_query()
        }

    def _update_device_commands(self, commands):
        self.device_commands.clear()
        for command in commands:
            self.device_commands[command.cmd_name] = command

    def _update_device_attributes(self, attributes):
        self.device_attributes.clear()
        for attribute in attributes:
            self.device_attributes[attribute.name] = attribute

    def interface_change_event_handler(self, event_data):
        """Handles tango device interface change events.

        Extracts neccesary data and calls :meth:`interface_change_callback` with
        said data.
        """
        if event_data.err:
            # Need to catch this, otherwise it is going to clear out the attribute
            # and command lists, respectively.
            self._logger.error(
                "Event system DevError(s) occured!!! %s", str(event_data.errors)
            )
            return

        received_timestamp = event_data.reception_date.totime()
        self._update_device_attributes(event_data.att_list)
        self._update_device_commands(event_data.cmd_list)
        self.interface_change_callback(
            event_data.device_name,
            received_timestamp,
            self.device_attributes,
            self.device_commands,
        )

    def attribute_event_handler(self, event_data):
        """Handles tango attribute events.

        Extracts neccesary data and calls :meth:`sample_event_callback` with
        said data.

        """
        # TODO NM 2016-04-06 Call a different callback for non-sample events,
        # i.e. error callbacks etc.
        if event_data.err:
            fqdn_attr_name = event_data.attr_name
            # tango://monctl.devk4.camlab.kat.ac.za:4000/mid_dish_0000/elt/
            # master/<attribute_name>#dbase=no
            # We process the FQDN of the attribute to extract just the
            # attribute name. Also handle the issue with the attribute name being
            # converted to lowercase in subsequent callbacks.
            attr_name_ = fqdn_attr_name.split("/")[-1].split("#")[0]
            attr_name = self.orig_attr_names_map[attr_name_.lower()]
            received_timestamp = event_data.reception_date.totime()
            quality = AttrQuality.ATTR_INVALID  # Events with errors do not send
            # the attribute value, so regard
            # its reading as invalid.
            timestamp = time.time()
            event_type = event_data.event
            value = event_data.attr_value
            self._logger.error("Event system DevError(s) occured!!! %s",
                               str(event_data.errors))
            self.sample_event_callback(attr_name, received_timestamp,
                                       timestamp, value, quality, event_type)

            return

        event_type = event_data.event
        received_timestamp = event_data.reception_date.totime()
        attr_value = event_data.attr_value
        name = attr_value.name
        value = attr_value.value
        quality = attr_value.quality
        timestamp = attr_value.time.totime()

        # A work around to remove the suffix "#dbase=no" string when using a
        # file as a database. Also handle the issue with the attribute name being
        # converted to lowercase in subsequent callbacks.
        name_trimmed = name.split("#")[0]
        attr_name = self.orig_attr_names_map[name_trimmed.lower()]
        self.sample_event_callback(
            attr_name, received_timestamp, timestamp, value, quality, event_type
        )

    def interface_change_callback(
        self, device_name, received_timestamp, attributes, commands
    ):
        """Callback called for the TANGO interface change event. NOP implementation.

        Intended for subclasses to override this method, or for the method to be
        replaced in instances

        Parameters
        ----------
        device_name: str
        received_timestamp: float
        attributes : dict
            Attribute names as keys, value is an instance of
            :class: `tango._tango.AttributeInfoEx`, a return value of
            :meth:`tango.DeviceProxy.get_attribute_config` of each attribute.
        commands : dict
            Command name as keys, value is instance of :class:`tango.CommandInfoEx`
            (the return value of :meth:`tango.DeviceProxy.command_list_query`)
            for each command.
        """
        pass

    def sample_event_callback(
        self, name, received_timestamp, timestamp, value, quality, event_type
    ):
        """Callback called for every sample event. NOP implementation.

        Intended for subclasses to override this method, or for the method to be
        replaced in instances

        Parameters

        """
        pass

    def _subscribe_to_event(self, event_type, attribute_name=None, warn_no_polling=True):

        dp = self.tango_dp
        subscribed = False
        try:
            if event_type == tango.EventType.INTERFACE_CHANGE_EVENT:
                self._interface_change_event_id = dp.subscribe_event(
                    event_type, self.interface_change_event_handler
                )
            else:
                event_id = dp.subscribe_event(
                    attribute_name,
                    event_type,
                    self.attribute_event_handler,
                    stateless=False
                )
                self._event_ids.add(event_id)
            subscribed = True
        except tango.DevFailed, exc:
            exc_reasons = {arg.reason for arg in exc.args}
            if 'API_AttributePollingNotStarted' in exc_reasons:
                if warn_no_polling:
                    self._logger.warning('TODO NM: Need to implement something for '
                                         'attributes that are not polled, processing '
                                         'attribute {}'.format(attribute_name))
            elif 'API_EventPropertiesNotSet' in exc_reasons:
                self._logger.info('Attribute {} has no event properties set'
                                    .format(attribute_name))
            else:
                raise
        return subscribed

    def setup_attribute_sampling(self, attributes=None, server_polling_fallback=False):
        """Subscribe to all or some types of Tango attribute events"""
        if server_polling_fallback:
            self._logger.warning(
                'Sampling may enable polling on device %s', self.tango_dp.name())
        attributes = attributes if attributes is not None else self.device_attributes
        for attr_name in sorted(attributes):
            # order of preference (for efficiency)
            # * change (leave polling unchanged)
            # * change (enable server polling)
            # * periodic (enable server polling)
            # TODO: add manual polling on client side instead of enabling
            #       polling on server.
            #       See gitlab.com/ska-telescope/web-maxiv-tangogql/-/blob/
            #           e1e4098f/tangogql/aioattribute/attribute.py#L120
            
            subscribed = self._subscribe_to_event(
                tango.EventType.CHANGE_EVENT,
                attr_name,
                warn_no_polling=not server_polling_fallback,
            )

            if not subscribed and server_polling_fallback:
                self._setup_attribute_polling(attr_name)
                events = self.device_attributes[attr_name].events
                if self._is_event_properties_set(events.ch_event):
                    subscribed = self._subscribe_to_event(
                        tango.EventType.CHANGE_EVENT, attr_name
                    )
                if not subscribed:
                    subscribed = self._subscribe_to_event(
                        tango.EventType.PERIODIC_EVENT, attr_name
                    )

            if not subscribed:
                self._logger.warning("Failed to subscribe to attribute '%s'", attr_name)
            # TODO: read initial value manually, if couldn't subscribe
            #       call sample_event_callback with AttrQuality.ATTR_INVALID
            #       since we are not getting updates.

    def _setup_attribute_polling(self, attribute_name, poll_period=1000):
        retry_time = 0.5  # in seconds
        retries = 2  # Maximum number of retries
        if not self.tango_dp.is_attribute_polled(attribute_name):
            _retries = 0
            retry = True
            while retry and _retries < retries:
                try:
                    self.tango_dp.poll_attribute(attribute_name, poll_period)
                except tango.DevFailed as exc:
                    exc_reasons = {arg.reason for arg in exc.args}
                    if "API_AlreadyPolled" in exc_reasons:
                        retry = False
                        self._logger.info(
                            "Attribute '%s' already polled" % attribute_name
                        )
                    else:
                        self._logger.warning(
                            "Setting polling on attribute '%s' failed on retry '%s'"
                            ". Retrying again..." % (attribute_name, _retries + 1),
                            exc_info=True,
                        )
                        _retries += 1
                        time.sleep(retry_time)
                else:
                    retry = False
                    self._logger.info(
                        "Polling on attribute '%s' was set up"
                        " successfully" % attribute_name
                    )

    def _is_event_properties_set(self, event_info):
        for attr in dir(event_info):
            if attr.startswith("__"):
                continue
            if getattr(event_info, attr) == "Not specified":
                return False
        return True

    def clear_attribute_sampling(self):
        """Unsubscribe from all Tango events previously subscribed to

        Cleanup for setup_attribute_sampling

        """
        while self._event_ids:
            event_id = self._event_ids.pop()
            try:
                self.tango_dp.unsubscribe_event(event_id)
            except tango.DevFailed as exc:
                exc_reasons = {arg.reason for arg in exc.args}
                if "API_EventNotFound" in exc_reasons:
                    self._logger.info("No event with id {} was set up.".format(event_id))
                else:
                    raise
