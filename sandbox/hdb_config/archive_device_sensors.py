from __future__ import division, print_function, absolute_import

import argparse

import PyTango

parser = argparse.ArgumentParser(description='Setup device archiving')
parser.add_argument('devices', nargs='+')
parser.add_argument('--poll-period', type=int, default=3000, help=
                    'Attribute polling period in ms')
parser.add_argument('--archive-event-period', type=int, default=None)
parser.add_argument('--archive-event-absolute', type=float, default=None)
parser.add_argument('--archive-event-relative', type=float, default=None)
parser.add_argument('--hdb-config-device', default='tango/hdb/cm-1')
parser.add_argument('--hdb-subscriber-device', default='tango/hdb/es-1')

def main(options):
    poll_period = options.poll_period
    ar_abs = options.archive_event_absolute
    ar_rel = options.archive_event_relative
    ar_per = options.archive_event_period
    archiver = options.hdb_subscriber_device
    cm_dev = PyTango.DeviceProxy(options.hdb_config_device)
    sys_url = 'tango://{}:{}/'.format(
        cm_dev.get_db_host(), cm_dev.get_db_port())
    cm_dev.Init()
    for device_name in options.devices:
        dev = PyTango.DeviceProxy(device_name)
        dev.ping()
        for attr_name in dev.get_attribute_list():
            attr_fqdn = sys_url + device_name + '/' + attr_name
            cm_dev.SetAttributeName = attr_fqdn
            if poll_period:
                cm_dev.SetPollingPeriod = poll_period
            if ar_abs:
                cm_dev.SetAbsoluteEvent = ar_abs
            if ar_rel:
                cm_dev.SetRelativeEvent = ar_rel
            if ar_per:
                cm_dev.SetPeriodEvent = ar_per
            cm_dev.SetCodePushedEvent = False
            cm_dev.SetArchiver = archiver
            cm_dev.AttributeAdd()
            cm_dev.ping()


if __name__ == '__main__':
    main(parser.parse_args())
