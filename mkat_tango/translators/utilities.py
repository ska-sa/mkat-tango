###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2016 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################
"""
    @author MeerKAT CAM team <cam@ska.ac.za>
"""
from __future__ import absolute_import, division, print_function
from future import standard_library
standard_library.install_aliases()  # noqa: E402

SENSOR_ATTRIBUTE_NAMES = {}


def katcpname2tangoname(sensor_name):
    """
    Removes the dash(es) in the sensor name and replaces them with underscore(s)
    to guard against illegal attribute identifiers in TANGO

    Parameters
    ----------
    sensor_name : str
    The name of the sensor. For example:

        'actual-azim' or 'acs.temperature-01''

    Returns
    -------
    attr_name : str
    The legal identifier for an attribute. For example:

        'actual_azim' or 'acs_temperature_01'
    """
    # TODO (KM) 13-06-2016 : Need to find a way to deal with sensor names with dots.
    attribute_name = sensor_name.replace("-", "_").replace(".", "_")
    SENSOR_ATTRIBUTE_NAMES[attribute_name] = sensor_name
    return attribute_name


def tangoname2katcpname(attribute_name):
    """
    Removes the underscore(s) in the attribute name and replaces them with
    dashe(s), so that we can access the the KATCP Sensors using their identifiers

    Parameters
    ----------
    attr_name : str
    The name of the sensor. For example:

        'actual_azim'

    Returns
    -------
    sensor_name : str
    The legal identifier for an attribute. For example:

        'actual-azim'
    """
    try:
        return SENSOR_ATTRIBUTE_NAMES[attribute_name]
    except KeyError:
        sensor_name = attribute_name.replace("_", "-")
        return sensor_name


def address(host_port):
    """Convert a HOST:PORT argument to a (host, port) tuple.
    Paramaters
    ----------
    host_port : str
        String consisting of HOST:PORT. HOST is optional. PORT is
        must be an integer.
    Returns
    -------
    host : str
        Hostname or dotted quad IP address.
    port : int
        Port number.
    """
    # Import here to prevent chicken-and-egg dependency issues in setup.py
    import argparse

    if ":" not in host_port:
        raise argparse.ArgumentTypeError("Address must contain a colon")
    host, port = host_port.split(":")
    try:
        port = int(port)
    except ValueError:
        raise argparse.ArgumentTypeError("Port must be an integer")
    return (host, port)
