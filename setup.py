#!/usr/bin/env python

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
          "PyTango>=9.2.0",
          "numpy",
          "enum",
          "katcore",
          "katproxy",
          "katcp"],
      tests_require=[
          'enum',
          'numpy',
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
