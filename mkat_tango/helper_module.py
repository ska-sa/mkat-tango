from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
from future import standard_library
standard_library.install_aliases()

import os
import sys


def get_server_name():
    """Gets the TANGO server name from the command line arguments

    Returns
    =======
    server_name : str
        tango device server name

    Note
    ====
    Extract the Tango server_name or equivalent executable
    (i.e.sim_xmi_parser.py -> sim_xmi_parser or
    /usr/local/bin/mkat-tango-katcpdevice2tango-DS ->
    mkat-tango-katcpdevice2tango-DS) from the command line
    arguments passed, where sys.argv[0] is the server executable name
    and sys.argv[1] is the server instance.

    """
    executable_name = os.path.split(sys.argv[0])[-1].split('.')[0]
    server_name = executable_name + '/' + sys.argv[1]
    return server_name
