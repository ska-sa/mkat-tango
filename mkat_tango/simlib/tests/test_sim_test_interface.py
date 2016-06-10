import time
import mock

from functools import partial

from addict import Dict

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
        self.sim_quantities['wind-speed'] = GaussianSlewLimited(
            mean=1, std_dev=20, max_slew_rate=3,
            min_bound=0, max_bound=100)
        self.sim_quantities['wind-direction'] = GaussianSlewLimited(
            mean=0, std_dev=150, max_slew_rate=60,
            min_bound=0, max_bound=359.9999)
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
        self.control_attributes = self._control_attributes()
        self.device_instance = sim_test_interface.SimControl.instances[
                self.device.name()]
        def cleanup_refs(): del self.device_instance
        self.addCleanup(cleanup_refs)

    def _control_attributes(self):
        """Function collects all the available models and gets all the
        adjustable_attributes which will be control attributes on the
        simulator test interface device.
        Returns
        =======
        control_attributes : list
            A list of all the adjustable attributes
        """
        control_attributes = []
        models = set([quant.__class__
                for quant in self.test_model.sim_quantities.values()])
        for cls in models:
            control_attributes += [attr for attr in cls.adjustable_attributes]
        return control_attributes

    def test_attribute_list(self):
        ADDITIONAL_IMPLEMENTED_ATTR = set([
            'Status',   # Tango library attribute
            'State',    # Tango library attribute
            'sensor_name',    # Attribute indentifier for sensor to be controlled
            'pause_active',    # Flag for pausing the model updates
            ])
        attributes = set(self.device.get_attribute_list())
        self.assertEqual(attributes - ADDITIONAL_IMPLEMENTED_ATTR,
                        set(self.control_attributes))

    def test_model_defaults(self):
        device_model = self.device_instance.model
        # test that the model instance of the sim control is the same one as Fixture
        self.assertEqual(device_model, self.test_model)
        # test that default values from the instantiated model match that of sim control
        for quantity in set(device_model.sim_quantities.keys()):
            model_quantity_type = device_model.sim_quantities[quantity]
            fixture_quantity_type = self.test_model.sim_quantities[quantity]
            self.assertEqual(model_quantity_type, fixture_quantity_type)
            self.device.sensor_name = quantity  # sets the sensor name for which
            # to evaluate the quantities to be controlled
            for attr in self.device.get_attribute_list():
                if attr in model_quantity_type.adjustable_attributes:
                    attribute_value = getattr(self.device, attr)
                    model_attr_value = getattr(fixture_quantity_type, attr)
                    if model_attr_value:
                        self.assertEqual(attribute_value, model_attr_value)

    def test_model_attribute_change(self):
        desired_sensor_name = 'relative-humidity'
        control_attr_dict = Dict()
        control_attr_dict.desired_mean = 60
        control_attr_dict.desired_min_bound = 5
        control_attr_dict.desired_max_bound = 100
        control_attr_dict.desired_std_dev = 2
        control_attr_dict.desired_max_slew_rate = 2
        control_attr_dict.desired_last_val = 62
        control_attr_dict.desired_last_update_time = time.time()
        self.device.sensor_name = desired_sensor_name
        # setting the desired attribute values for the device's attributes
        # that can be controlled
        for attr in self.device.get_attribute_list():
            if attr in self.control_attributes:
                val = getattr(control_attr_dict, 'desired_' + attr)
                setattr(self.device, attr, val)
        # Here the test_model_defaults is called to quanify the changes on the model
        self.test_model_defaults()
