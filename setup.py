#!/usr/bin/env python
###############################################################################
# SKA South Africa (http://ska.ac.za/)                                        #
# Author: cam@ska.ac.za                                                       #
# Copyright @ 2019 SKA SA. All rights reserved.                               #
#                                                                             #
# THIS SOFTWARE MAY NOT BE COPIED OR DISTRIBUTED IN ANY FORM WITHOUT THE      #
# WRITTEN PERMISSION OF SKA SA.                                               #
###############################################################################

import sys
from setuptools import setup, find_packages

setup(name="mkat_tango",
      description="Work relating to the use of tango in MeerKAT and for SKA.",
      author="SKA SA KAT-7 / MeerKAT CAM team",
      author_email="cam@ska.ac.za",
      packages=find_packages(),
      url='https://github.com/ska-sa/mkat-tango',
      classifiers=[
          "Intended Audience :: Developers",
          "Programming Language :: Python :: 2",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: Scientific/Engineering :: Astronomy",
      ],
      platforms=["OS Independent"],
      setup_requires=["katversion"],
      use_katversion=True,
      install_requires=[
          "PyTango>=9.2.2",
          "numpy>=1.17" if sys.version_info >= (3, 5) else "numpy<1.17",
          "tornado>=4.3, <5",
          "katcp",
          "tango-simlib"],
      tests_require=[
          'numpy>=1.17' if sys.version_info >= (3, 5) else 'numpy<1.17',
          'nose_xunitmp'],
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'mkat-tango-weather-DS = mkat_tango.simulators.weather:weather_main',
              'mkat-tango-AP-DS = mkat_tango.simulators.mkat_ap_tango:main',
              'mkat-tango-tangodevice2katcp = mkat_tango.translators.katcp_tango_proxy:tango2katcp_main',
              'mkat-tango-katcpdevice2tango-DS = mkat_tango.translators.tango_katcp_proxy:main',
              'mkat-tango-tango_launcher = mkat_tango.translators.tango_launcher:main',
          ]},
      )
