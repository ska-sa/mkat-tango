"""
MeerKAT AP simulator.
    @author MeerKAT CAM team <cam@ska.ac.za>
"""

from devicetest import DeviceTestCase
import logging

# DUT
from mkat_tango.simulators.mkat_tango_ap import MkatAntennaPositioner

class test_MkatAntennaPositioner(DeviceTestCase):
    
    device = MkatAntennaPositioner

    expected_attributes = frozenset(['mode', 'requested_azim', 'requested_elev',
                                     'failure_present', 'actual_azim', 'actual_elev',
                                     'requested_azim_rate', 'requested_elev_rate',
                                     'actual_azim_rate', 'actual_elev_rate',
                                     'State', 'Status'])
    
    
    def setUp(self):
        super(test_MkatAntennaPositioner, self).setUp()
        self.instance = MkatAntennaPositioner.instances[self.device.name()]

    def tearDown(self):
        self.instance = None


#    def test_model_instantiation(self):
#        TODO
#
#    def test_model_thread_started(self):
#        TODO

    def test_stop(self):
        self.assertEqual(self.device.mode, 'shutdown')
        self.device.slew()
        self.assertNotEqual(self.device.mode, 'stop')
  
#    def test_slew(self):
#        TODO
#
#    def test_maintenance(self):
#        TODO
#
#    def test_rate(self):
#        TODO
#
#    def test_stow(self):
#        TODO

    def test_attribute_values(self):
        #attributes = set(self.device.get_attribute_list())
        #attr = self.device.get_device_attr()
        
        self.assertEqual(self.device.mode, 'shutdown')
        self.assertEqual(self.device.requested_azim, 0.0)
        self.assertEqual(self.device.requested_elev, 90.0)
        self.assertEqual(self.device.failure_present, False)
        self.assertEqual(self.device.actual_azim, 0.0)
        self.assertEqual(self.device.actual_elev, 90.0)
        self.assertEqual(self.device.requested_azim_rate, 0.0)
        self.assertEqual(self.device.requested_elev_rate, 0.0)
        self.assertEqual(self.device.actual_azim_rate, 0.0)
        self.assertEqual(self.device.actual_elev_rate, 0.0)
        self.assertEqual(self.device.State, 'OFF')
        self.assertEqual(self.device.Status, 'The device is in OFF state')

    def test_attribute_list(self):
        attributes = set(self.device.get_attribute_list())
        self.assertEqual(attributes, self.expected_attributes)

#    def test_write_attributes(self):
#        TODO
#
#    def test_command_list(self):
#        TODO

    
    
