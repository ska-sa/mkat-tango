import time
import mock

from functools import partial

from devicetest import DeviceTestCase

from mkat_tango.simlib import sim_test_interface, model, quantities

class FixtureModel(model.Model):

    def setup_sim_quantities(self):
        start_time = self.start_time
        GaussianSlewLimited = partial(
            quantities.GaussianSlewLimited, start_time=start_time)
        ConstantQuantity = partial(
            quantities.ConstantQuantity, start_time=start_time)

        self.sim_quantities['relative-humidity'] = GaussianSlewLimited(
            mean=65, std_dev=10, max_slew_rate=10,
            min_bound=0, max_bound=150)
        self.sim_quantities['input-comms-ok'] = ConstantQuantity(start_value=True)
        super(FixtureModel, self).setup_sim_quantities()

    def reset_model(self):
        self.setup_sim_quantities()

class test_SimControl(DeviceTestCase):
    device = sim_test_interface.SimControl

    @classmethod
    def setUpClass(cls):
        cls.test_model = FixtureModel('mkat_sim/nodb/simcontrol')
        super(test_SimControl, cls).setUpClass()

    def setUp(self):
        super(test_SimControl, self).setUp()
        self.test_model.reset_model()
        self.control_attributes = []
        self.device_instance = sim_test_interface.SimControl.instances[
                self.device.name()]
        def cleanup_refs(): del self.device_instance
        self.addCleanup(cleanup_refs)

    def test_attribute_list(self):
        ADDITIONAL_IMPLEMENTED_ATTR = set([
            'Status',   # Tango library attribute
            'State',    # Tango library attribute
            'sensor_name',    # Attribute indentifier for sensor to be controlled
            'pause_active',    # Flag for pausing the model updates
            ])
        models = set([quant.__class__
            for quant in self.test_model.sim_quantities.values()])
        attributes = set(self.device.get_attribute_list())
        for cls in models:
            self.control_attributes += [attr for attr in cls.adjustable_attributes]
        self.assertEqual(attributes - ADDITIONAL_IMPLEMENTED_ATTR,
                        set(self.control_attributes))

    def test_model_defaults(self):
        device_model = self.device_instance.model
        # test that the model instance of the sim control is the one same as Fixture
        self.assertEqual(device_model, self.test_model)
        # test that default values from the instantiated model match that of sim control
        for quantity in device_model.sim_quantities.keys():
            model_quantity_type = device_model.sim_quantities[quantity]
            fixture_quantity_type = self.test_model.sim_quantities[quantity]
            self.assertEqual(model_quantity_type, fixture_quantity_type)
            #from IPython import embed; embed()
            self.device.sensor_name = quantity  # sets the sensor name for which
            # to evaluate the quantities to be controlled
            for attr in self.device.get_attribute_list():
                if attr in self.control_attributes:
                    attribute_value = getattr(self.device, attr, None)
                    model_attr_value = getattr(fixture_quantity_type, None)
                    self.assertEqual(attribute_value, model_attr_value)
