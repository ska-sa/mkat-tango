#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################


import logging
from PyTango import DevState

MODULE_LOGGER = logging.getLogger(__name__)

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
        tango_dev.set_state(DevState.ON)

    def action_Off(self, model, tango_dev=None, data_input=None):
        """Changest the State of the device to OFF.
        """
        tango_dev.set_state(DevState.OFF)

    def action_Do_Something(self, model, tango_dev=None, data_input=None):
        """Do something using the arguments passed on by the command executer.
        """
        # TODO(KM 20-12-2016) Redefine method to take in arguments and use them to
        # change the state of the device
        return "Do_Something returning"

    def action_Stop_Rainfall(self, model, tango_dev=None, data_input=None):
        """Totally sets the simulated quantity rainfall to a constant value of zero.
        """
        try:
            quant_rainfall = model.sim_quantities['rainfall']
        except KeyError:
            MODULE_LOGGER.debug("Quantity rainfall not in the model")
        else:
            quant_rainfall.max_bound = 0.0

# TODO(KM 15-12-2016) Will need to define action methods that take in inputs and returns
# some values that correspond to the dtype_out of the TANGO command.
