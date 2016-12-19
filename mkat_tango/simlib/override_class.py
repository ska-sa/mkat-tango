from PyTango import DevState

class Override_Weather(object):
    """An override class for the TANGO device class 'Weather'. It provides all the
    implementations of the command handler functions for the commands specified in the
    POGO generated XMI data description file.
    """
    def __init__(self):
        """This constructor method takes in nothing and does nothing.
        """
        pass

    def action_On(self, model, tango_dev=None, data_input=None):
        """Changes the State of the device to ON.
        """
        # Need to update when hooking it up to the TANGO device.
        tango_dev.set_state(DevState.ON)

    def action_Off(self, model, tango_dev=None, data_input=None):
        """Changest the State of the device to OFF.
        """
        # Need to update when hooking it up to the TANGO device.
        tango_dev.set_state(DevState.OFF)

    def action_Do_Something(self, model, tango_dev=None, data_input=None):
        """Do something using the arguments passed on by the command executer.
        """
        # Need to update when hooking it up to the TANGO device.
        #self.doing_something(args)
        return "Do_Something returning"

    # Might need to define this action in the SIMDD commands, for testing purposes
    def action_Stop_Rainfall(self, model, tango_dev=None, data_input=None):
        """
        """
        try:
            quant_rainfall = model.sim_quantities['rainfall']
        except KeyError:
            print "Quantity not in the model"
        quant_rainfall.max_bound = 0.0

# TODO(KM 15-12-2016) Will need to define action methods that take in inputs and returns
# some values that correspond to the dtype_out of the TANGO command.
