class Override(object):
    """
    """
    def __init__(self):
        """
        """
        pass
        #self.sim_model = model
        #self.device = tango_device

    def action_On(self, model):
        """Changes the State of the device to ON.
        """
        #self.device.set_state(DevState.ON)
        return "On returning"

    def action_Off(self, model):
        """Changest the State of the device to OFF.
        """
        #self.device.set_state(DevState.OFF)
        return "Off returning"


    def action_Do_Something(self, model, *args):
        """Do something using the arguments passed on by the command executer.
        """
        #self.doing_something(args)
        return "Do_Something returning"

    def action_Stop_Rainfall(self, model):
        """
        """
        try:
            quant_rainfall = self.sim_model.sim_quantities['Rainfall']
        except KeyError:
            print "Quantity not in the model"
        quant_rainfall.max_bound = 0.0

 

#The API that every override class should comply with:
#
 #   - all the methods should be prefixed with the word "action_"
  #  - the __init__ method should be called with the 
