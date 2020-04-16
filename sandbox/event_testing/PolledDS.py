from __future__ import absolute_import, print_function, division


from future import standard_library
standard_library.install_aliases()
from builtins import *
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
