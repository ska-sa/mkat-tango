import unittest

from mkat_tango.simlib import quantities

class test_Quantity(unittest.TestCase):
    def test_init(self):
        """Test initialisation of Quantity instance"""
        desired_start_value = 'polony'
        desired_start_time = 5

        # Quantity is an ABC with and abstract next_val method
        # so we must override it
        class TestQuantity(quantities.Quantity):
            def next_val(self, t):
                pass

        DUT = TestQuantity(
            start_value=desired_start_value,
            start_time=desired_start_time)

        # Test that start_value and start_time parameters are
        # stored as the correct attributes
        self.assertEqual(DUT.last_update_time,
                         desired_start_time)
        self.assertEqual(DUT.last_val,
                         desired_start_value)

        # Check default value constructor
        DUT = TestQuantity()
        # Default time = current time
