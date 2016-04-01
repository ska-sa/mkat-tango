from devicetest import DeviceTestCase

from mkat_tango.simulators import AntennaPositionerDS

class test_AntennaPositiner(DeviceTestCase):
    '''Simple test cases for device attributes'''
    device = AntennaPositionerDS.AntennaPositioner

    def test_mode(self):
        print self.device.mode

    def test_requested_azimuth(self):
        print self.device.requested_azimuth

    def test_requested_elevation(self):
        print self.device.requested_elevation

    def test_actual_azimuth(self):
        print self.device.actual_azimuth

    def test_actual_elevation(self):
        print self.device.actual_elevation
