#!/usr/bin/env python
from __future__ import absolute_import, print_function, division

import PyTango
import time

########################################
# Running the mkat_tango_ap simulator. #
########################################

# Get the device proxy to expose device server attributes and commands
device_proxy = PyTango.DeviceProxy("test/mkat_ap/1")

# NB: All attributes are read-only, but commands are used to change their values.

# Device testing using available commands

# 1.Maintenance (Request mode maintenance)
device_proxy.Maintanance()

# 2.Rate (Request the AP to move the antenna at the rate specified)
# Input: list containing azim & elev velocities.
device_proxy.Rate([0.5, 1.0])

# 3.Slew (Request the AP to slew)
# Input: list containing azim & elev positions.
device_proxy.Slew([15.0, 0.0])
time.sleep(5)

# 4.Stop (Request mode stop)
device_proxy.Stop()

# 5.Stow (Request mode stow)
device_proxy.Stow()

# 6.Clear_Track_Stack (Clear the stack with the track samples)
device_proxy.Clear_Track_Stack()

# 7.Enable_Point_Error_Refraction (enable/disable the compensation for
# RF refraction provided by the ACU)
# Input - boolean
device_proxy.Enable_Point_Error_Refraction(True)

# 8.Reset_Failures (Informs the AP to clear/acknowledge any failures)
device_proxy.Reset_Failures()

# 9.Set_Indexer_Position (select receiver indexer position)
# Input : string [select from: 'l', 'x', 'u', 's']
device_proxy.Set_Indexer_Position("l")

# 10.Set_On_Source_Threshold (set the threshold for the "not-on-source" condition)
# Input : double [between 0.0 and 1.0]
device_proxy.Set_On_Source_Threshold(0.5)

# 11.Track_Az_El (AP to set the antenna at the position specified by the azimuth and
# elevation parameters at a specified time)
# Input : list containing timestamp, azim & azim position
# timestamp - The time when the position coordinates should be applied
device_proxy.Track_Az_El([time.time() + 5, -10.0, 20.0])

# 12 Track (AP to start tracking using the position samples provided by the Track_az_el)
device_proxy.Track()
time.sleep(5)

# --------------------------------------------------------------------------------------
device_proxy.Stop()
# ======================================================================================
