# PolledDS.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

import time
import sys
import logging

from PyTango import Database, DbDevInfo
from PyTango import server as TS


class Polled(TS.Device):
    @TS.attribute(
        dtype="DevBoolean", doc="An example scalar boolean attribute", polling_period=1000
    )
    def ScalarBool(self):
        print("Getting ScalarBool at {}".format(time.time()))
        return True


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(module)s - "
        "%(pathname)s : %(lineno)d - %(message)s",
        level=logging.INFO,
    )

    if "--register" in sys.argv:
        reg_ind = sys.argv.index("--register")
        sys.argv.pop(reg_ind)
        name = sys.argv.pop(reg_ind)
        db = Database()
        dev_info = DbDevInfo()
        dev_info._class = "Polled"
        dev_info.server = "PolledDS/polled"
        dev_info.name = name
        db.add_device(dev_info)
    else:
        TS.server_run([Polled])
