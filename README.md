# mkat-tango

Work relating to the use of tango in MeerKAT and for SKA


Events and Polling
==================
Periodic event type - an event is sent at a fixed periodic interval. The frequency of this event is determined by
the event_period property of the attribute and the polling frequency. The polling frequency deter-
mines the highest frequency at which the attribute is read. The event_period determines the highest frequency at 
which the periodic event is sent.

------------------------------------------------------------
Also noted that when polling at a period of less than 50 ms, tango becomes inconsistent with the updates generated. i.e. the observed time difference between updates fluctuates (50+-20 ms)
