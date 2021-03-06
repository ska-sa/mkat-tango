# register_FestivalDS.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

import PyTango

db = PyTango.Database()


def add_new_device(server, klass, device):
    dev_info = PyTango.DbDevInfo()
    dev_info.name = device
    dev_info.klass = klass
    dev_info.server = server
    db.add_device(dev_info)


# Create a PyAlarm device
add_new_device("FestivalDS/kataware", "FestivalDS", "mkat/festival/kataware")

print("Succefully registered FestivalDS in Tango-DB")
print("==========================================")
