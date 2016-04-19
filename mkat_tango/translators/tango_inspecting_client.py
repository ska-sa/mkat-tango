class TangoInspectingClient(object):
    def __init__(self, tango_device_proxy):
        self.tango_dp = tango_device_proxy
        self.device_attributes = {}
        self.device_commands = {}
        # True if the stored device attributes and commands are potentially out of date
        self._dirty = True

    def inspect(self):
        self.device_attributes = self.inspect_attributes()
        self.device_commands = self.inspect_commands()
        self._dirty = False     # TODO need to consider race conditions

    def inspect_attributes(self):
        return {attr_name: self.tango_dp.get_attribute_config(attr_name)
                for attr_name in self.tango_dp.get_attribute_list()}

    def inspect_commands(self):
        return {cmd_info.cmd_name: cmd_info
                for cmd_info in self.tango_dp.command_list_query()}
