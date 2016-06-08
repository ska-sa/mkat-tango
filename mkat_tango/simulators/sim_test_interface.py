import time
import weakref
import logging
import PyTango
import numpy

from PyTango import UserDefaultAttrProp
from PyTango import AttrQuality, DevState
from PyTango import Attr, AttrWriteType, WAttribute
from PyTango import DevString, DevDouble, DevBoolean
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command

import model
from model import Model

class SimControl(Device):
    __metaclass__ = DeviceMeta

    instances = weakref.WeakValueDictionary()

    def init_device(self):
        super(SimControl, self).init_device()

        name = self.get_name()
        self.instances[name] = self
        # Get the name of the device
        self.device_name = 'mkat_sim/' + name.split('/', 1)[1]
        self.model_instance = Model.model_registry[self.device_name]
        # Get the device instance model to be controlled
        self.model = Model.model_registry[self.device_name]
        # Get a list of attributes a device contains from the model
        self.device_sensors = self.model.sim_quantities.keys()
        self.set_state(DevState.ON)
        self.model_quantities = None
        self._sensor_name = ''
        self._pause_active = False

    # Static attributes of the device

    @attribute(dtype=str)
    def sensor_name(self):
        return self._sensor_name

    @sensor_name.write
    def sensor_name(self, name):
        if name in self.device_sensors:
            self._sensor_name = name
            self.model_quantities = self.model.sim_quantities[self._sensor_name]
        else:
            raise NameError('Name does not exist in the sensor list {}'.
                            format(self.device_sensors))

    @attribute(dtype=bool)
    def pause_active(self):
        return self._pause_active

    @pause_active.write
    def pause_active(self, isActive):
        self._pause_active = isActive
        setattr(self.model, 'paused', isActive)

    def initialize_dynamic_attributes(self):
        '''The device method that sets up attributes during run time'''
        # Get attributes to control the device model quantities
        # from class variables of the quantities included in the device model.
        models = set([quant.__class__
                      for quant in self.model.sim_quantities.values()])
        control_attributes = []

        for cls in models:
            control_attributes += [attr for attr in cls.adjustable_attributes]

        # Add a list of float attributes from the list of Guassian variables
        for attribute_name in control_attributes:
            model.MODULE_LOGGER.info(
                "Added weather {} attribute control".format(attribute_name))
            attr_props = UserDefaultAttrProp()
            attr = Attr(attribute_name, DevDouble, AttrWriteType.READ_WRITE)
            attr.set_default_properties(attr_props)
            self.add_attribute(attr, self.read_attributes, self.write_attributes)

    def read_attributes(self, attr):
        '''Method reading an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to read from.
        '''
        name = attr.get_name()
        self.info_stream("Reading attribute %s", name)
        attr.set_value(getattr(self.model_quantities, name))

    def write_attributes(self, attr):
        '''Method writing an attribute value
        Parameters
        ==========
        attr : PyTango.DevAttr
            The attribute to write to.
        '''
        name = attr.get_name()
        data = attr.get_write_value()
        self.info_stream("Writing attribute {} with value: {}".format(name, data))
        attr.set_value(data)
        setattr(self.model_quantities, name, data)
        if name == 'last_val' and self._pause_active:
            self.model.quantity_state[self._sensor_name] = data, time.time()
        else:
            setattr(self.model_quantities, name, data)

