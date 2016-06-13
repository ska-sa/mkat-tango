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
    properties = dict(model_key='the_test_model')

    @classmethod
    def setUpClass(cls):
        cls.test_model = FixtureModel('the_test_model')
        super(test_SimControl, cls).setUpClass()

    def setUp(self):
        super(test_SimControl, self).setUp()
        self.addCleanup(self.test_model.reset_model)
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
            control_attributes += [attr for attr in cls.adjustable_attributes
                    if attr not in control_attributes]
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
        self.assertIs(device_model, self.test_model)
        default_model = FixtureModel(
                'random_test_name',
                time_func=lambda: self.test_model.start_time)
        self._compare_models(device_model, default_model)

    def _compare_models(self, device_model, default_model):
        """Function compares two models to confirm value similaritiesi
        Parameters
        ==========
        device_model : device instance model
        default_model : default instance test model
        """
        # test that default values from the instantiated model match that of sim control
        for quantity in device_model.sim_quantities.keys():
            self.device.sensor_name = quantity  # sets the sensor name for which
            # to evaluate the quantities to be controlled
            desired_quantity = default_model.sim_quantities[quantity]
            for attr in self.test_model.sim_quantities[quantity].adjustable_attributes:
                attribute_value = getattr(self.device, attr)
                if hasattr(desired_quantity, attr):
                    model_attr_value = getattr(desired_quantity, attr)
                    self.assertEqual(attribute_value, model_attr_value)

    def _control_attr_dict(self, sensor_name):
        """Function generate a dictionary of all the control
        quantities of the test model.
        Returns
        =======
        control_attr_dict : dict
            A dictionary of all control model quantities
        """
        desired_sensor_name = sensor_name
        control_attr_dict = {}
        control_attr_dict['desired_mean'] = 600
        control_attr_dict['desired_min_bound'] = 50
        control_attr_dict['desired_max_bound'] = 1000
        control_attr_dict['desired_std_dev'] = 200
        control_attr_dict['desired_max_slew_rate'] = 200
        control_attr_dict['desired_last_val'] = 62
        control_attr_dict['desired_last_update_time'] = time.time()
        self.device.sensor_name = desired_sensor_name
        return control_attr_dict

    def _quants_before_dict(self):
        """Function generate a dictionary of all the default
        quantity values of the initial test model.
        Returns
        =======
        quants_before : dict
            A dictionary of all default model quantity values
        """
        self.test_model.reset_model()
        quants_before = {}
        # default values of the model quantities before the attributes change
        for quant_name, quant in self.test_model.sim_quantities.items():
            quants_before[quant_name] = {attr: getattr(quant, attr)
                    for attr in quant.adjustable_attributes}
        return quants_before

    def test_model_attribute_change(self):
        # setting the desired attribute values for the device's attributes
        # that can be controlled and checking if new values are actually
        # different to from the defualt.
        quants_before = self._quants_before_dict()
        desired_sensor_name = 'relative-humidity'
        for attr in self.control_attributes:
            new_val = self._control_attr_dict(desired_sensor_name)[
                    'desired_' + attr]
            setattr(self.device, attr, new_val)
            self.assertNotEqual(getattr(self.device, attr),
                    quants_before[desired_sensor_name][attr])
        # Compare the modified quantities and check if the other
        # quantities have not changed
        self._compare_models(self.device_instance.model, self.test_model)

        # Changing the second quantity to see modification and making sure
        # the other quantities are not modified
        quants_before = self._quants_before_dict()
        desired_sensor_name = 'wind-speed'
        for attr in self.control_attributes:
            new_val = self._control_attr_dict(desired_sensor_name)[
                    'desired_' + attr]
            setattr(self.device, attr, new_val)
            self.assertNotEqual(getattr(self.device, attr),
                    quants_before[desired_sensor_name][attr])
        # Compare the modified quantities and check if the other
        # quantities have not changed
        self._compare_models(self.device_instance.model, self.test_model)
