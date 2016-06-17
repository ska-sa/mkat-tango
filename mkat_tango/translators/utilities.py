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
    @author MeerKAT CAM team <cam@ska.ac.za>
"""

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
    #TODO (KM) 13-06-2016 : Need to find a way to deal with sensor names with dots.
    attribute_name = sensor_name.replace('-', '_').replace('.', '_')
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
    sensor_name = attribute_name.replace('_', '-')
    return sensor_name
