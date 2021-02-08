#!/usr/bin/env python
# mkat_ap_model_instantiator.py
# -*- coding: utf8 -*-
# vim:fileencoding=utf8 ai ts=4 sts=4 et sw=4
# Copyright 2016 National Research Foundation (South African Radio Astronomy Observatory)
# BSD license - see LICENSE for details

"""
MeerKAT AP simulator.
    @author MeerKAT CAM team <cam@ska.ac.za>
"""
from __future__ import absolute_import, division, print_function
from future import standard_library

standard_library.install_aliases()

from katproxy.sim.mkat_ap import MkatApModel

if __name__ == "__main__":
    ap_model = MkatApModel()
    ap_model.start()
