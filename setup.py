#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="mkat_tango",
    description="Work relating to the use of tango in MeerKAT and for SKA.",
    author="SKA SA KAT-7 / MeerKAT CAM team",
    author_email="cam@ska.ac.za",
    packages=find_packages(),
    url="https://github.com/ska-sa/mkat-tango",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Astronomy",
    ],
    platforms=["OS Independent"],
    setup_requires=["katversion"],
    use_katversion=True,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    install_requires=[
        "PyTango>=9.3.2",
        "numpy",
        "tornado>=4.3, <5",
        "katcp",
        "tango-simlib>=0.5.0",
        "future",
        "futures; python_version<'3'",
    ],
    tests_require=["numpy", "nose_xunitmp"],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "mkat-tango-weather-DS = mkat_tango.simulators.weather:weather_main",
            "mkat-tango-AP-DS = mkat_tango.simulators.mkat_ap_tango:main",
            ("mkat-tango-tangodevice2katcp = "
             "mkat_tango.translators.katcp_tango_proxy:tango2katcp_main"),
            ("mkat-tango-katcpdevice2tango-DS = "
             "mkat_tango.translators.tango_katcp_proxy:main"),
            "mkat-tango-tango_launcher = mkat_tango.translators.tango_launcher:main",
        ]
    },
)
