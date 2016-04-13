class TangoInspectingClient(object):
    def __init__(self, tango_device_proxy):
        self.tango_dp = tango_device_proxy

    def inspect_attributes(self):
        return {attr_name: self.tango_dp.get_attribute_config(attr_name)
                for attr_name in self.tango_dp.get_attribute_list()}
