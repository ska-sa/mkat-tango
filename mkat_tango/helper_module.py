import os
import sys

def get_server_name():
    """Gets the server name from the command line arguments

    Returns
    =======
    server_name : str
        tango device server name

    Note
    ====
    Extract the server_name or equivalent executable
    (i.e.sim_xmi_parser.py -> sim_xmi_parser or
    from the command line arguments passed, where sys.argv[1]
    is the server instance.

    """
    executable_name = os.path.split(sys.argv[0].split('.')[0])[1]
    server_name = executable_name + '/' + sys.argv[1]
    return server_name