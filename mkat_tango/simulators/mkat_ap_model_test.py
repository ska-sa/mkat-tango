#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2013 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
MeerKAT AP simulator.
    @author MeerKAT CAM team <cam@ska.ac.za>
"""

from mkat_ap import MkatApModel


if __name__ == "__main__":
    # Instantiate an Mkat AP model and then run it
    ap_model = MkatApModel()
    ap_model.start()

#    print ap_model.mode()
#    ap_model.set_mode('slew')
#    ap_model._stopEvent.is_set()
#    ap_model.slew(23.4, 56.9)
#    ap_model.get_sensor('actual-azim')
#    ap_model.get_sensor('actual-azim').value()
#    ap_model = MkatApModel()
#    ap_model.get_sensor('actual-azim')
#    az = ap_model.get_sensor('actual-azim')
#    az.value()
#    cntrl = ap_model.get_sensor('control')
#    cntrl.value()
#    d_status = ap_model.get_sensor('device-status')
#    d_status.value()
#    ap_model.mode()
#    ap_model.stopped()
#    ap_model.set_mode('safe1')
#    ap_model.set_mode('stowing')
#    ap_model.WARN_HORN_SOUND_TIME
