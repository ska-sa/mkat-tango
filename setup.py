#!/usr/bin/env python
from setuptools import setup, find_packages

setup (
    name = "mkat_tango",
    version = "0.0.0dev",
    description = " Work relating to the use of tango in MeerKAT and for SKA",
    author = "SKA SA KAT-7 / MeerKAT CAM team",
    author_email = "cam@ska.ac.za",
    packages = find_packages(),
    url='https://github.com/ska-sa/mkat-tango',
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
    platforms = [ "OS Independent" ],
    install_requires = ["PyTango>=8.1.5"],
    zip_safe = False,
)
