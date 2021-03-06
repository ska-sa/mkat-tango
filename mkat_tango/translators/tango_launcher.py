#!/usr/bin/env python
# tango_launcher.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

"""Utility to help launch a TANGO device in a KATCP eco-system
Helps by auto-registering a TANGO device if needed
"""
from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

from builtins import range

import os
import sys
import argparse

import tango

from functools import partial

parser = argparse.ArgumentParser(
    description="Launch a TANGO device, handling registration as needed. "
    "Assumes a separate server process per device (for now?)."
)

required_argument = partial(parser.add_argument, required=True)

required_argument(
    "--name",
    action="append",
    help="TANGO name(s) for the devices i.e.specified multiple times",
)
required_argument(
    "--class",
    dest="device_class",
    action="append",
    help="TANGO class name(s) for the device(s) i.e. specified the "
    + "same number of times and the names and classes are matched in order",
)
required_argument("--server-command", help="TANGO server executable command")
required_argument("--server-instance", help="TANGO server instance name")
required_argument("--port", help="TCP port where TANGO server should listen")
parser.add_argument(
    "--put-device-property",
    action="append",
    help="Put a device property into the TANGO DB, format is: "
    "'device/name/X:property_name:property_value'. Only allows "
    "properties to be set on devices started with this command. "
    "Can be specified multiple times.",
    dest="device_properties",
    default=[],
)


def register_device(name, device_class, server_name, instance):
    dev_info = tango.DbDevInfo()
    dev_info.name = name
    dev_info._class = device_class
    dev_info.server = "{}/{}".format(server_name, instance)
    print(
        """Attempting to register TANGO device {!r}
    class: {!r}  server: {!r}.""".format(
            dev_info.name, dev_info._class, dev_info.server
        )
    )
    db = tango.Database()
    db.add_device(dev_info)


def put_device_property(dev_name, property_name, property_value):
    db = tango.Database()
    print(
        "Setting device {!r} property {!r}: {!r}".format(
            dev_name, property_name, property_value
        )
    )
    db.put_device_property(dev_name, {property_name: [property_value]})


def start_device(opts):
    server_name = os.path.basename(opts.server_command)
    if server_name.endswith(".py"):
        server_name = server_name.split(".")[0]
    number_of_devices = len(opts.name)
    # Register tango devices
    for i in range(number_of_devices):
        register_device(
            opts.name[i], opts.device_class[i], server_name, opts.server_instance
        )
    for dev_property in opts.device_properties:
        try:
            dev_name, dev_property_name, dev_property_val = dev_property.split(":", 2)
        except ValueError:
            raise ValueError(
                "Device property incorrectly specified, "
                "see help for --put-device-property"
            )
        assert dev_name in opts.name, "Device {!r} not launched by this command".format(
            dev_name
        )
        put_device_property(dev_name, dev_property_name, dev_property_val)

    if opts.server_command.endswith(".py"):
        args = ["python %s" % opts.server_command, opts.server_instance]
        print(
            "Starting TANGO device server:\n{}".format(
                " ".join(["{!r}".format(arg) for arg in args])
            )
        )
        sys.stdout.flush()
        sys.stderr.flush()
        os.system(" ".join(args))
    else:
        args = [
            opts.server_command,
            opts.server_instance,
            "-ORBendPoint",
            "giop:tcp::{}".format(opts.port),
        ]
        print(
            "Starting TANGO device server:\n{}".format(
                " ".join(["{!r}".format(arg) for arg in args])
            )
        )
        sys.stdout.flush()
        sys.stderr.flush()
        os.execvp(opts.server_command, args)


def main():
    opts = parser.parse_args()
    start_device(opts)


if __name__ == "__main__":
    main()
