# register_ap_ds.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

import PyTango

ap_name = "mkat_sim/ap/1"

dev_info = PyTango.DbDevInfo()
dev_info.server = "mkat-tango-AP-DS/test"
dev_info._class = "MkatAntennaPositioner"
dev_info.name = ap_name
db = PyTango.Database()
db.add_device(dev_info)
print("Registration of antenna positioner Successful")
