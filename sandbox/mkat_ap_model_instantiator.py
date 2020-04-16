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
from __future__ import absolute_import, print_function, division


from katproxy.sim.mkat_ap import MkatApModel

if __name__ == "__main__":
    ap_model = MkatApModel()
    ap_model.start()
