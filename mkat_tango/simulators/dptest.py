from PyTango import DeviceProxy

class DeviceProxyTest(DeviceProxy):
    def __init__(self, dev_name):
        DeviceProxy.__init__(self, dev_name)
        #self.test = test
   
    def assert_request_succeeds(self, command_name, *params, **kwargs):
        """Assert that given request succeeds when called with given parameters.

        Optionally also checks the arguments.

        Parameters
        ----------
        requestname : str
            The name of the request.
        params : list of objects
            The parameters with which to call the request.
        args_echo : bool, optional
            Keyword parameter.  Assert that the reply arguments after 'ok'
            equal the request parameters.  Takes precedence over args_equal,
            args_in and args_length. Defaults to False.
        args_equal : None or list of strings, optional
            Keyword parameter.  Assert that the reply arguments after 'ok'
            equal this list.  Ignored if args_echo is present; takes precedence
            over args_echo, args_in and args_length.
        args_in : None or list of lists, optional
            Keyword parameter.  Assert that the reply arguments after 'ok'
            equal one of these tuples.  Ignored if args_equal or args_echo is
            present; takes precedence over args_length.
        args_length : None or int, optional
            Keyword parameter.  Assert that the length of the reply arguments
            after 'ok' matches this number. Ignored if args_equal, args_echo or
            args_in is present.
        informs_count : None or int, optional
            Keyword parameter.  Assert that the number of informs received
            matches this number, if not None.

        """
        #[K]reply, informs = self.blocking_request(Message.request(requestname,
                                                              # *params))
        reply = self.command_inout(command_name)
        reply_name = self.command_query(command_name).cmd_name

        #[K]self.test.assertEqual(reply.name, requestname, "Reply to request '%s'"
            #                  " has name '%s'." % (requestname, reply.name))
        self.test.assertEqual(reply_name, command_name, "Reply to request '%s'"
                              "has name '%s'." % (command_name, reply_name))

        #[K]msg = ("Expected request '%s' called with parameters %r to succeed, "
          #     "but it failed %s."
          #     % (requestname, params, ("with error '%s'" % reply.arguments[1]
           #                             if len(reply.arguments) >= 2 else
            #                            "(with no error message)")))

        msg = ("Expected request '%s' called with parameters %r to succeed, "
               "but it failed %s."
               % (command_name, params, ("with error '%s'" % reply[1]
                                         if len(reply) >= 2 else
                                         "(with no error message)")))
        #[K]self.test.assertTrue(reply.reply_ok(), msg)
        self.test.assertTrue(reply[0]=='ok', msg)


    
    def assert_request_fails(self, command_name, *params, **kwargs):
        """Assert that given request fails when called with given parameters.

        Parameters
        ----------
        requestname : str
            The name of the request.
        params : list of objects
            The parameters with which to call the request.
        status_equals : string, optional
            Keyword parameter. Assert that the reply status equals this
            string.
        error_equals : string, optional
            Keyword parameter. Assert that the error message equals this
            string.

        """
        #[K]reply, informs = self.blocking_request(Message.request(requestname,
         #                                                      *params))
        reply = self.command_inout(command_name)
        reply_name = self.command_query(command_name).cmd_name
        
        #[K]msg = "Reply to request '%s' has name '%s'." % (requestname, reply.name)
        msg = "Reply to command '%s' has name '%s'." % (command_name, reply_name)
        #[K]self.test.assertEqual(reply.name, requestname, msg)
        self.test.assertEqual(reply_name, command_name, msg)

        #[K]msg = ("Expected request '%s' called with parameters %r to fail, "
               #"but it was successful." % (requestname, params))
        msg = ("Expected request '%s' called with parameters %r to fail, "
               "but it was successful." % (command_name, params))
        #[K]self.test.assertFalse(reply.reply_ok(), msg)
        self.test.assertFalse(reply[0]=='ok', msg)

        