# -*- coding: utf-8 -*-
"""
Created on Tue Apr  5 11:35:14 2016

@author: kmadisa
"""

from mkat_ap import MkatApModel

if __name__ == "__main__":
    ap_model = MkatApModel()
    ap_model.start()
    
    print ap_model.mode()
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
#    ap_model.run()
#    ap_model.WARN_HORN_SOUND_TIME