import time
import logging
import unittest
import textwrap
import mock

import tornado.testing
import tornado.gen
import devicetest

from devicetest import TangoTestContext
from katcp import Message
from katcp.testutils import mock_req
from katcp.testutils import start_thread_with_cleanup, BlockingTestClient
from katcore.testutils import cleanup_tempfile

from mkat_tango.translators.tests.test_tango_inspecting_client import (
    TangoTestDevice, ClassCleanupUnittestMixin)

from mkat_tango import testutils
from mkat_tango.translators import katcp_tango_proxy

LOGGER = logging.getLogger(__name__)

KATCP_REQUEST_DOC_TEMPLATE = textwrap.dedent(
    """
    ?{cmd_name} {dtype_in} -> {dtype_out}

    Input Parameter
    ---------------

    {doc_in}

    Returns
    -------

    {doc_out}
    """).lstrip()


class TangoDevice2KatcpProxy_BaseMixin(ClassCleanupUnittestMixin):
    DUT = None

    @classmethod
    def setUpClassWithCleanup(cls):
        cls.tango_db = cleanup_tempfile(cls, prefix='tango', suffix='.db')
        cls.tango_context = TangoTestContext(TangoTestDevice, db=cls.tango_db)
        start_thread_with_cleanup(cls, cls.tango_context)
        cls.tango_device_address = cls.tango_context.get_device_access()
        devicetest.Patcher.unpatch_device_proxy()

    def setUp(self):
        super(TangoDevice2KatcpProxy_BaseMixin, self).setUp()
        self.DUT = katcp_tango_proxy.TangoDevice2KatcpProxy.from_addresses(
            ("", 0), self.tango_device_address)
        if hasattr(self, 'io_loop'):
            self.DUT.set_ioloop(self.io_loop)
            self.io_loop.add_callback(self.DUT.start)
            self.addCleanup(self.DUT.stop, timeout=None)
        else:
            start_thread_with_cleanup(self, self.DUT, start_timeout=1)
        self.katcp_server = self.DUT.katcp_server
        self.tango_device_proxy = self.tango_context.device
        self.tango_test_device = TangoTestDevice.instances[self.tango_device_proxy.name()]
        self.katcp_address = self.katcp_server.bind_address
        self.host, self.port = self.katcp_address


class test_TangoDevice2KatcpProxy(
        TangoDevice2KatcpProxy_BaseMixin, unittest.TestCase):

    def setUp(self):
        super(test_TangoDevice2KatcpProxy, self).setUp()
        self.client = BlockingTestClient(self, self.host, self.port)
        start_thread_with_cleanup(self, self.client, start_timeout=1)
        self.client.wait_protocol(timeout=1)

    def test_from_address(self):
        self.assertEqual(self.client.is_connected(), True)
        reply, informs = self.client.blocking_request(Message.request('watchdog'))
        self.assertTrue(reply.reply_ok(), True)

    def test_sensor_attribute_match(self):
        reply, informs = self.client.blocking_request(Message.request('sensor-list'))
        sensor_list = set([inform.arguments[0] for inform in informs])
        attribute_list = set(self.tango_device_proxy.get_attribute_list())
        NOT_IMPLEMENTED_SENSORS = set(['ScalarDevEncoded'])
        self.assertEqual(attribute_list - NOT_IMPLEMENTED_SENSORS, sensor_list,
            "\n\n!KATCP server sensor list differs from the TangoTestServer "
            "attribute list!\n\nThese sensors are"
            " extra:\n%s\n\nFound these attributes with no corresponding sensors:\n%s"
            % ("\n".join(sorted([str(t) for t in sensor_list - attribute_list])),
               "\n".join(sorted([str(t) for t in attribute_list - sensor_list]))))

    def test_initial_attribute_sensor_values(self):
        sensors = self.katcp_server.get_sensors()
        attributes = self.tango_test_device.attr_return_vals
        for sensor in sensors:
            sensor_value = sensor.value()
            if sensor.name in ['State', 'Status']:
                # This sensors are handled specially since they are tango library
                # Attributes with State returning a device state object
                if sensor.name in ['State']:
                    state = str(self.tango_device_proxy.state())
                    # tango._PyTango.DevState.ON is device state object
                    self.assertEqual(sensor_value, state)
                else:
                    status = self.tango_device_proxy.status()
                    self.assertEqual(sensor_value, status)
            else:
                attribute_value = attributes[sensor.name][0]
                if sensor.name in ['ScalarDevEnum']:
                    self.assertEqual(set(['ONLINE', 'OFFLINE', 'RESERVE']),
                                     set(sensor.params))
                    self.assertEqual(sensor_value, sensor.params[attribute_value])
                else:
                    self.assertEqual(sensor_value, attribute_value)

    def test_attribute_sensor_update(self):
        sensors = []
        observers = {}
        # when polling at a period of less than 50 ms, tango becomes
        # inconsistent with the updates generated  i.e. the observed
        # time difference between updates fluctuates (50+-20 ms)
        poll_period = 50
        num_periods = 10
        # sleep time is 10 poll periods plus a little
        sleep_time = poll_period/1000. * (num_periods + 0.5)
        testutils.set_attributes_polling(self, self.tango_device_proxy,
                           self.tango_test_device, {attr: poll_period
                           for attr in self.tango_device_proxy.get_attribute_list()})
        EXCLUDED_ATTRS = set([
                'State',    # Tango library attribute, Cannot change event_period
                'Status',   # Tango library attribute, Cannot change event_period
                'ScalarDevEncoded'   # Not implemented sensor, to be removed once
                # attribute type DevEncoded is handled as katcp server sensor types
                ])

        for attr_name in self.tango_device_proxy.get_attribute_list():
            if attr_name not in EXCLUDED_ATTRS:
                # Instantiating observers and attaching them onto the katcp
                # sensors to allow logging of periodic event updates into a list
                observers[attr_name] = observer = SensorObserver()
                self.katcp_server.get_sensor(attr_name).attach(observer)
                sensors.append(attr_name)
            else:
                LOGGER.debug('Found unexpected attributes')
        time.sleep(sleep_time)

        for sensor in sensors:
            self.katcp_server.get_sensor(sensor).detach(observer)
            obs = observers[sensor]
            self.assertAlmostEqual(len(obs.updates), num_periods, delta=2)

    def test_requests_list(self):
        tango_td = self.tango_test_device
        self.client.test_help((
            ('Init', '?Init DevVoid -> DevVoid'),
            ('Status', '?Status DevVoid -> DevString'),
            # TODO NM 2016-05-20 Need to check what State should actually be and implement
            ('State', '?State DevVoid -> DevState'),
            ('ReverseString', KATCP_REQUEST_DOC_TEMPLATE.format(
                cmd_name='ReverseString',  **tango_td.ReverseString_command_kwargs)),
            ('MultiplyInts', KATCP_REQUEST_DOC_TEMPLATE.format(
                 cmd_name='MultiplyInts', **tango_td.MultiplyInts_command_kwargs)),
            ('Void', KATCP_REQUEST_DOC_TEMPLATE.format(
                cmd_name='Void', dtype_in='DevVoid', doc_in='Void',
                dtype_out='DevVoid', doc_out='Void')),
            ('MultiplyDoubleBy3', KATCP_REQUEST_DOC_TEMPLATE.format(
                cmd_name='MultiplyDoubleBy3',
                **tango_td.MultiplyDoubleBy3_command_kwargs)),
        ))

    def test_request(self):
        mid=5
        reply, _ = self.client.blocking_request(Message.request(
            'ReverseString', 'polony', mid=mid))
        self.assertEqual(str(reply),
                         "!ReverseString[{}] ok ynolop".format(mid))

class test_TangoDevice2KatcpProxyAsync(TangoDevice2KatcpProxy_BaseMixin,
                                       tornado.testing.AsyncTestCase):

    @tornado.gen.coroutine
    def _test_cmd_handler(self, cmd_name, request_args, expected_reply_args):
        device_proxy = self.tango_context.device
        device_proxy_spy = mock.Mock(wraps=device_proxy)
        cmd_info = device_proxy.command_query(cmd_name)
        handler = katcp_tango_proxy.tango_cmd_descr2katcp_request(
            cmd_info, device_proxy_spy)

        ## Check that the docstring is correct
        # Do dict(...) to make a copy so that we don't mess with the original
        command_kwargs = dict(getattr(self.tango_test_device,
                                 cmd_name+'_command_kwargs'))
        if 'dtype_in' not in command_kwargs:
            command_kwargs['dtype_in'] = 'DevVoid'
            command_kwargs['doc_in'] = 'Void'
        if 'dtype_out' not in command_kwargs:
            command_kwargs['dtype_out'] = 'DevVoid'
            command_kwargs['doc_out'] = 'Void'

        expected_docstring = KATCP_REQUEST_DOC_TEMPLATE.format(
            cmd_name=cmd_name, **command_kwargs)
        self.assertEqual(handler.__doc__, expected_docstring)

        ## To a test request
        mock_katcp_server = mock.Mock(spec_set=self.DUT.katcp_server)
        req = mock_req(cmd_name, *request_args, server=mock_katcp_server)
        result = yield handler(mock_katcp_server, req, req.msg)
        # check if expected reply is recieved
        expected_msg = Message.reply(cmd_name, *expected_reply_args)
        self.assertEqual(str(result), str(expected_msg))
        # check that tango device proxy is called once and only once.
        self.assertEqual(device_proxy_spy.command_inout.call_count, 1)

    @tornado.testing.gen_test
    def test_cmd2request_ReverseString(self):
        """Test request handler for the TangoTestServer ReverseString command

        """
        yield self._test_cmd_handler(cmd_name='ReverseString',
                                     request_args=['abcdef'],
                                     expected_reply_args=['ok', 'fedcba'])

    @tornado.testing.gen_test
    def test_cmd2request_MultiplyInts(self):
        """Test request handler for the TangoTestServer MultiplyInts command

        """
        yield self._test_cmd_handler(cmd_name='MultiplyInts',
                                     request_args=[1, 3, 7, 9],
                                     expected_reply_args=['ok', 1*3*7*9])

    @tornado.testing.gen_test
    def test_cmd2request_MultiplyInt(self):
        """Test request handler for the TangoTestServer MultiplyInts command
        with a single item

        """
        yield self._test_cmd_handler(cmd_name='MultiplyInts',
                                     request_args=[88],
                                     expected_reply_args=['ok', 88])

    @tornado.testing.gen_test
    def test_cmd2request_MultiplyDoubleBy3(self):
        """Test request handler for the TangoTestServer MultiplyDoubleBy2MultiplyInts command

        """
        yield self._test_cmd_handler(cmd_name='MultiplyDoubleBy3',
                                     request_args=[0.5],
                                     expected_reply_args=['ok', 0.5*3.0])

    @tornado.testing.gen_test
    def test_cmd2request_Void(self):
        """Test request handler for the TangoTestServer ReverseString command

        """
        yield self._test_cmd_handler(cmd_name='Void',
                                     request_args=[],
                                     expected_reply_args=['ok'])

    @tornado.testing.gen_test
    def test_cmd2request_State(self):
        """Test request handler for the TangoTestServer State command

        """
        yield self._test_cmd_handler(cmd_name='State',
                                     request_args=[],
                                     expected_reply_args=['ok', 'ON'])

class SensorObserver(object):
    def __init__(self):
        self.updates = []

    def update(self, sensor, reading):
        self.updates.append((sensor, reading))
        LOGGER.debug('Received {!r} for attr {!r}'.format(sensor, reading))
