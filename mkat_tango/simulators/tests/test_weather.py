from devicetest import DeviceTestCase

# DUT
from mkat_tango.simulators import weather

class test_Weather(DeviceTestCase):
    device = weather.Weather
    def test_temperature(self):
        print self.device.temperature
