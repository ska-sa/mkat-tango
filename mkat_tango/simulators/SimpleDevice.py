from katcp import DeviceServer, Sensor

class SimpleDevice(DeviceServer):
    def setup_sensors(self):

        # Temperature sensor
        self.temperature_sensor = Sensor.float(
            "temperature",
            "Device temperature",
            "degrees",
            default=25.0
        )
        self.add_sensor(self.temperature_sensor)

        # Humidity sensor
        self.humidity_sensor = Sensor.float(
            "humidity",
            "Device humidity",
            "percent",
            default=50.0
        )
        self.add_sensor(self.humidity_sensor)

    def request_echo(self, req, msg):
        """Echo back the message argument.

        :param msg: The message to echo.
        """
        if len(msg.arguments) < 1:
            return req.reply("fail", "Missing argument")
        return req.reply("ok", msg.arguments[0])

    def request_hello(self, req):
        """Echo back the message argument."""
        return req.reply("hello system demo 3")

if __name__ == "__main__":
    import sys
    host = "0.0.0.0"
    port = 7147
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    server = SimpleDevice(host, port)
    server.start()
