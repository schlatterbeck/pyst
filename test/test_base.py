from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import unicode_literals
import sys
import os
import socket
import unittest
from   subprocess import Popen
from   asterisk.manager import Manager
from   asterisk.compat import Queue, string_types
from   asterisk.astemu import Event, AsteriskEmu
from   asterisk.agi import AGI, AGIDBError

class Test_Manager(unittest.TestCase):
    """ Test the asterisk management interface.
    """

    default_events = AsteriskEmu.default_events

    def close(self):
        if self.manager:
            self.manager.close()
            self.manager = None
        self.astemu.close()

    def setUp(self):
        self.manager  = None
        self.childpid = None
        self.events   = []
        self.evcount  = 0
        self.queue    = Queue()

    def tearDown(self):
        self.close()

    def handler(self, event, manager):
        self.events.append(event)
        self.queue.put(self.evcount)
        self.evcount += 1

    def run_manager(self, chatscript):
        self.astemu = AsteriskEmu (chatscript)
        self.port = self.astemu.port
        self.manager = Manager()
        self.manager.connect('localhost', port = self.port)
        self.manager.register_event ('*', self.handler)

    def compare_result(self, r_event, event):
        for k, v in event.items():
            if k == 'CONTENT':
                self.assertEqual(r_event.data, v)
            elif isinstance(v, string_types):
                self.assertEqual(r_event[k], v)
            else:
                self.assertEqual(r_event[k], v[-1])
                self.assertEqual(sorted(r_event.multiheaders[k]),
                    sorted(list(v)))

    def test_login(self):
        self.run_manager({})
        r = self.manager.login('account', 'geheim')
        self.compare_result(r, self.default_events['Login'][0])
        self.close()
        self.assertEqual(self.events, [])

    def test_command(self):
        d = dict
        events = dict \
            ( Command =
                ( Event
                    ( Response  = ('Follows',)
                    , Privilege = ('Command',)
                    , CONTENT   = 
"""Channel              Location             State   Application(Data)
lcr/556              s@attendoparse:9     Up Read(dtmf,,30,noanswer,,2)    
1 active channel
1 active call
372 calls processed
--END COMMAND--\r
"""
                    )
                ,
                )
            )
        self.run_manager(events)
        r = self.manager.command ('core show channels')
        self.assertEqual(self.events, [])
        self.compare_result(r, events['Command'][0])

    def test_redirect(self):
        d = dict
        events = dict \
            ( Redirect =
                ( Event
                    ( Response  = ('Success',)
                    , Message   = ('Redirect successful',)
                    )
                ,
                )
            )
        self.run_manager(events)
        r = self.manager.redirect \
            ('lcr/556', 'generic', 'Bye', context='attendo')
        self.assertEqual(self.events, [])
        self.compare_result(r, events['Redirect'][0])

    def test_originate(self):
        d = dict
        events = dict \
            ( Originate =
                ( Event
                    ( Response  = ('Success',)
                    , Message   = ('Originate successfully queued',)
                    )
                , Event
                    ( Event            = ('Newchannel',)
                    , Privilege        = ('call,all',)
                    , Channel          = ('lcr/557',)
                    , ChannelState     = ('1',)
                    , ChannelStateDesc = ('Rsrvd',)
                    , CallerIDNum      = ('',)
                    , CallerIDName     = ('',)
                    , AccountCode      = ('',)
                    , Exten            = ('',)
                    , Context          = ('',)
                    , Uniqueid         = ('1332366541.558',)
                    )
                , Event
                    ( Event            = ('NewAccountCode',)
                    , Privilege        = ('call,all',)
                    , Channel          = ('lcr/557',)
                    , Uniqueid         = ('1332366541.558',)
                    , AccountCode      = ('4019946397',)
                    , OldAccountCode   = ('',)
                    )
                , Event
                    ({ 'Event'           : ('NewCallerid',)
                     , 'Privilege'       : ('call,all',)
                     , 'Channel'         : ('lcr/557',)
                     , 'CallerIDNum'     : ('',)
                     , 'CallerIDName'    : ('',)
                     , 'Uniqueid'        : ('1332366541.558',)
                     , 'CID-CallingPres' :
                        ('0 (Presentation Allowed, Not Screened)',)
                    })
                , Event
                    ( Event            = ('Newchannel',)
                    , Privilege        = ('call,all',)
                    , Channel          = ('lcr/558',)
                    , ChannelState     = ('1',)
                    , ChannelStateDesc = ('Rsrvd',)
                    , CallerIDNum      = ('',)
                    , CallerIDName     = ('',)
                    , AccountCode      = ('',)
                    , Exten            = ('',)
                    , Context          = ('',)
                    , Uniqueid         = ('1332366541.559',)
                    )
                , Event
                    ( Event            = ('Newstate',)
                    , Privilege        = ('call,all',)
                    , Channel          = ('lcr/558',)
                    , ChannelState     = ('4',)
                    , ChannelStateDesc = ('Ring',)
                    , CallerIDNum      = ('0000000000',)
                    , CallerIDName     = ('',)
                    , Uniqueid         = ('1332366541.559',)
                    )
                , Event
                    ( Event            = ('Newstate',)
                    , Privilege        = ('call,all',)
                    , Channel          = ('lcr/558',)
                    , ChannelState     = ('7',)
                    , ChannelStateDesc = ('Busy',)
                    , CallerIDNum      = ('0000000000',)
                    , CallerIDName     = ('',)
                    , Uniqueid         = ('1332366541.559',)
                    )
                , Event
                    ({ 'Event'         : ('Hangup',)
                     , 'Privilege'     : ('call,all',)
                     , 'Channel'       : ('lcr/558',)
                     , 'Uniqueid'      : ('1332366541.559',)
                     , 'CallerIDNum'   : ('0000000000',)
                     , 'CallerIDName'  : ('<unknown>',)
                     , 'Cause'         : ('16',)
                     , 'Cause-txt'     : ('Normal Clearing',)
                    })
                , Event
                    ({ 'Event'         : ('Hangup',)
                     , 'Privilege'     : ('call,all',)
                     , 'Channel'       : ('lcr/557',)
                     , 'Uniqueid'      : ('1332366541.558',)
                     , 'CallerIDNum'   : ('<unknown>',)
                     , 'CallerIDName'  : ('<unknown>',)
                     , 'Cause'         : ('17',)
                     , 'Cause-txt'     : ('User busy',)
                    })
                , Event
                    ( Event            = ('OriginateResponse',)
                    , Privilege        = ('call,all',)
                    , Response         = ('Failure',)
                    , Channel          = ('LCR/Ext1/0000000000',)
                    , Context          = ('linecheck',)
                    , Exten            = ('1',)
                    , Reason           = ('1',)
                    , Uniqueid         = ('<null>',)
                    , CallerIDNum      = ('<unknown>',)
                    , CallerIDName     = ('<unknown>',)
                    )
                )
            )
        self.run_manager(events)
        r = self.manager.originate \
            ('LCR/Ext1/0000000000', '1'
            , context   = 'linecheck'
            , priority  = '1'
            , account   = '4019946397'
            , variables = {'CALL_DELAY' : '1', 'SOUND' : 'abandon-all-hope'}
            )
        self.compare_result(r, events['Originate'][0])
        for k in events['Originate'][1:]:
            n = self.queue.get()
            self.compare_result(self.events[n], events['Originate'][n+1])

    def test_misc_events(self):
        d = dict
        # Events from SF bug 3470641 
        # http://sourceforge.net/tracker/
        # ?func=detail&aid=3470641&group_id=76162&atid=546272
        # But we fail to reproduce the bug.
        events = dict \
            ( Login =
                ( self.default_events['Login'][0]
                , Event
                    ({ 'AppData'    : '0?begin2'
                     , 'Extension'  : 'zap2dahdi'
                     , 'Uniqueid'   : '1325950970.698'
                     , 'Priority'   : '9'
                     , 'Application': 'GotoIf'
                     , 'Context'    : 'macro-dial-one'
                     , 'Privilege'  : 'dialplan,all'
                     , 'Event'      : 'Newexten'
                     , 'Channel'    : 'Local/102@from-queue-a8ca;2'
                    })
                , Event
                    ({ 'Value'     : '2'
                     , 'Variable'  : 'MACRO_DEPTH'
                     , 'Uniqueid'  : '1325950970.698'
                     , 'Privilege' : 'dialplan,all'
                     , 'Event'     : 'VarSet'
                     , 'Channel'   : 'Local/102@from-queue-a8ca;2'
                    })
                , Event
                    ({'Privilege': 'dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 9\r\n'
                      'Application: GotoIf\r\n'
                      'AppData: 0?begin2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 10\r\n'
                      'Application: Set\r\n'
                      'AppData: THISDIAL=SIP/102\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: THISDIAL\r\n'
                      'Value: SIP/102\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 11\r\n'
                      'Application: Return\r\n'
                      'AppData: \r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: GOSUB_RETVAL\r\n'
                      'Value: \r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: dstring\r\n'
                      'Priority: 9\r\n'
                      'Application: Set\r\n'
                      'AppData: DSTRING=SIP/102&\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: DSTRING\r\n'
                      'Value: SIP/102&\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: dstring\r\n'
                      'Priority: 10\r\n'
                      'Application: Set\r\n'
                      'AppData: ITER=2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 6\r\n'
                      'Application: ExecIf\r\n'
                      'AppData: 0?Set(THISPART2=DAHDI/101)\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: ITER\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/102@from-queue-a8ca;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.698\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 7\r\n'
                      'Application: Set\r\n'
                      'AppData: NEWDIAL=SIP/101&\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: NEWDIAL\r\n'
                      'Value: SIP/101&\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 8\r\n'
                      'Application: Set\r\n'
                      'AppData: ITER2=2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: ITER2\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 9\r\n'
                      'Application: GotoIf\r\n'
                      'AppData: 0?begin2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: MACRO_DEPTH\r\n'
                      'Value: 2\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: Newexten\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Context: macro-dial-one\r\n'
                      'Extension: zap2dahdi\r\n'
                      'Priority: 10\r\n'
                      'Application: Set\r\n'
                      'AppData: THISDIAL=SIP/101\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2\r\n'
                      'Variable: THISDIAL\r\n'
                      'Value: SIP/101\r\n'
                      'Uniqueid: 1325950970.696\r\n'
                      '\r\n'
                      'Event: VarSet\r\n'
                      'Privilege: dialplan,all\r\n'
                      'Channel: Local/101@from-queue-4406;2'
                    , 'Variable': 'MACRO_DEPTH'
                    , 'Event': 'VarSet'
                    , 'Value': '2'
                    , 'Uniqueid': '1325950970.696'
                   })
                )
            )
        self.run_manager(events)
        r = self.manager.login('account', 'geheim')
        self.compare_result(r, events['Login'][0])
        evnames = []
        for s in events['Login'][3]['Privilege'].split('\r\n'):
            if s.startswith('Event:'):
                evnames.append(s.split(':')[1].strip())
        for k in range(30):
            n = self.queue.get()
            e = self.events[n]
            if n < 2:
                self.compare_result(e, events['Login'][n+1])
            elif n == 2:
                self.assertEqual(e['Event'], 'VarSet')
            else:
                self.assertEqual(e['Event'], evnames[n-3])
        self.assertEqual(len(self.events), 30)

    def test_agent_event(self):
        d = dict
        # Events from SF bug 3470641 
        # http://sourceforge.net/tracker/
        # ?func=detail&aid=3470641&group_id=76162&atid=546272
        # But we fail to reproduce the bug.
        events = dict \
            ( Login =
                ( self.default_events['Login'][0]
                , Event
                    ( Event              = ('AgentCalled',)
                    , Privilege          = ('agent,all',)
                    , Queue              = ('test',)
                    , AgentCalled        = ('SIP/s394000',)
                    , AgentName          = ('910567',)
                    , ChannelCalling     = ('SIP/multifon-00000006',)
                    , DestinationChannel = ('SIP/s394000-00000007',)
                    , CallerIDNum        = ('394000',)
                    , CallerIDName       = ('Agent',)
                    , Context            = ('from-multifon',)
                    , Extension          = ('7930456789',)
                    , Priority           = ('3',)
                    , Uniqueid           = ('1302010429.6',)
                    , Variable           = ('data1=456789', 'data2=test')
                    )
                )
            )
        self.run_manager(events)
        r = self.manager.login('account', 'geheim')
        self.compare_result(r, events['Login'][0])
        for k in events['Login'][1:]:
            n = self.queue.get()
            self.compare_result(self.events[n], events['Login'][n+1])

class AGI_Emu(object):
    """ Test AGI: behave like an asterisk counterpart for testing AGI
        Note that we can't test some side effects like produced by
        'say_digits' or 'goto_on_exit' that are not visible in the
        command-exchange. But we can provide correct error messages etc.

        AGI initial handshake is mostly taken from
        http://www.asteriskdocs.org/en/2nd_Edition/asterisk-book-html-chunk
        /asterisk-CHP-9-SECT-5.html
    """

    def __init__(self, stdin=None, stdout=None, stderr=None):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.variables={}
        self.database={}
        print("agi_request: testscript.py", file=self.stdout)
        print("agi_channel: Zap/1-1", file=self.stdout)
        print("agi_language: en", file=self.stdout)
        print("agi_type: Zap", file=self.stdout)
        print("agi_uniqueid: 1116732890.8", file=self.stdout)
        print("agi_callerid: 101", file=self.stdout)
        print("agi_calleridname: Tom Jones", file=self.stdout)
        print("agi_callingpres: 0", file=self.stdout)
        print("agi_callingani2: 0", file=self.stdout)
        print("agi_callington: 0", file=self.stdout)
        print("agi_callingtns: 0", file=self.stdout)
        print("agi_dnid: unknown", file=self.stdout)
        print("agi_rdnis: unknown", file=self.stdout)
        print("agi_context: incoming", file=self.stdout)
        print("agi_extension: 141", file=self.stdout)
        print("agi_priority: 2", file=self.stdout)
        print("agi_enhanced: 0.0", file=self.stdout)
        print("agi_accountcode:", file=self.stdout)
        print("", file=self.stdout)
        self.stdout.flush()

        print("Init done", file=self.stderr)

    known_commands = dict.fromkeys \
        (( "ANSWER"
        ,  "HANGUP"
        ,  "record_file"
        ,  "say_digits"
        ,  "stream_file"
        ))

    def run(self):
        """ Read single line, check if the received command is known,
            call the command function if we have one or directly issue a
            200 response if we have no handler. If the command is
            unknown we directly return an error.
        """
        print("In Emu.run", file=self.stderr)
        while True:
            line = self.stdin.readline()
            if not line:
                break
            print("Recv: %s" % line, file=self.stderr)
            tokens = line.split()
            if len(tokens) < 1:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                break
            cmd = getattr(self, 'cmd_' + tokens[0].lower(), None)
            if tokens[0] in self.known_commands:
                print("200 result=0", file=self.stdout)
                self.stdout.flush()
            elif cmd:
                cmd(*tokens[1:])
            else:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()

    def cmd_database(self, *args):
        if not 3 <= len(args) <= 4:
            print("500 result=-1", file=self.stdout)
            self.stdout.flush()
            return
        print ("database: %s" % ','.join (args), file=self.stderr)
        k1, k2 = (args[i].strip('"') for i in range(1, 3))
        if args[0] == 'DEL':
            if len(args) != 3:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            if k1 not in self.database:
                self.database[k1] = {}
            if k2 in self.database[k1]:
                del self.database[k1][k2]
                print("200 result=1", file=self.stdout)
                self.stdout.flush()
                return
            else:
                print("200 result=0", file=self.stdout)
                self.stdout.flush()
                return
        if args[0] == 'DELTREE':
            if len(args) != 3:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            if k1 in self.database:
                del self.database[k1]
                print("200 result=1", file=self.stdout)
                self.stdout.flush()
                return
            else:
                print("200 result=0", file=self.stdout)
                self.stdout.flush()
                return
        if args[0] == 'GET':
            print ("db: %s" % self.database, file=self.stderr)
            if len(args) != 3:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            if k1 not in self.database:
                self.database[k1] = {}
            v = self.database[k1].get (k2, None)
            if v:
                print("200 result=1 (%s)" % v, file=self.stdout)
                self.stdout.flush()
                return
            else:
                print("200 result=0", file=self.stdout)
                self.stdout.flush()
                return
        elif args[0] == 'PUT':
            if len(args) != 4:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            if k1 not in self.database:
                self.database[k1] = {}
            self.database [k1][k2] = args[3].strip ('"')
            print ("after put db: %s" % self.database, file=self.stderr)
            print("200 result=1 (%s)" % args[3], file=self.stdout)
            self.stdout.flush()
            return
        else:
            print("500 result=-1", file=self.stdout)
            self.stdout.flush()
            return

    def cmd_get(self, *args):
        if not 2 <= len(args) <= 4:
            print("500 result=-1", file=self.stdout)
            self.stdout.flush()
            return
        if args[0] == 'DATA':
            print("200 result=1", file=self.stdout)
            self.stdout.flush()
            return
        if args[0] not in ('VARIABLE', 'FULL'):
            print("500 result=-1", file=self.stdout)
            self.stdout.flush()
            return
        if args[0] == 'VARIABLE':
            k = args[1].strip('"')
            if len(args) != 2:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            if k in self.variables:
                print("200 result=1 (%s)" % self.variables[k],
                    file=self.stdout)
                self.stdout.flush()
                return
            else:
                print("200 result=0", file=self.stdout)
                self.stdout.flush()
                return
        if args[0] == 'FULL':
            if args[1] != 'VARIABLE':
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            k = args[2].strip('"')
            if len(k) < 3:
                print("500 result=-1", file=self.stdout)
                self.stdout.flush()
                return
            print("get full: args=%s" % ','.join(args), file=self.stderr)
            if not k.startswith('$'):
                print("200 result=0", file=self.stdout)
                self.stdout.flush()
                return
            if k[1]=='{' and k[-1] == '}':
                v = self.variables.get(k[2:-1], None)
                if v:
                    print("200 result=1 (%s)" % v, file=self.stdout)
                    self.stdout.flush()
                    return
                else:
                    print("200 result=0", file=self.stdout)
                    self.stdout.flush()
                    return
            # Don't handle other cases
            print("200 result=0", file=self.stdout)
            self.stdout.flush()
            return
        
    def cmd_set(self, *args):
        if len(args) != 3:
            print("500 result=-1", file=self.stdout)
            self.stdout.flush()
            return
        if args[0] != 'VARIABLE':
            print("500 result=-1", file=self.stdout)
            self.stdout.flush()
            return
        self.variables[args[1].strip ('"')] = args[2].strip ('"')
        print("200 result=1", file=self.stdout)
        self.stdout.flush()
    


class Test_AGI(unittest.TestCase):
    def setUp(self):
        # Create pipes, one from test to agi, one from agi to test
        pipe = os.pipe()
        self.stdin = os.fdopen(pipe[0], 'r')
        self.stdin_w = os.fdopen(pipe[1], 'w')
        pipe = os.pipe()
        self.stdout = os.fdopen(pipe[1], 'w')
        self.stdout_r = os.fdopen(pipe[0], 'r')
        # For now set stderr to None, we may want to capture this in the
        # future and compare the output in a test.
        self.stderr = open('/dev/null', 'w')
        # Fork process, tie correct ends of pipe to subprocess and call
        # AGI_Emu in subprocess.
        pid = os.fork()
        if pid: # parent
            self.stdin_w.close()
            self.stdout_r.close()
            self.stdin_orig = sys.stdin
            self.stdout_orig = sys.stdout
            sys.stdin = self.stdin
            sys.stdout = self.stdout
            self.pid = pid
        else: # child
            self.stdin.close ()
            self.stdout.close()
            sys.stdout = self.stdin_w
            sys.stdin = self.stdout_r
            emu = AGI_Emu(sys.stdin, sys.stdout, self.stderr)
            emu.run()
            os._exit(0)
        self.agi = AGI(sys.stdin, sys.stdout, self.stderr)

    def tearDown(self):
        sys.stdin.close()
        sys.stdout.close()
        self.stderr.close()
        sys.stdin = self.stdin_orig
        sys.stdout = self.stdout_orig
        os.waitpid(self.pid, 0)

    def test_variables(self):
        self.agi.set_variable('foo', 'bar')
        self.assertEqual(self.agi.get_variable('foo'), 'bar')
        self.assertEqual(self.agi.get_full_variable('${foo}'), 'bar')
        self.assertEqual(self.agi.get_variable('foobar'), '')

    def test_database(self):
        self.agi.database_put('foo', 'bar', 'foobar')
        self.agi.database_put('foo', 'baz', 'foobaz')
        self.agi.database_put('foo', 'bat', 'foobat')
        self.assertEqual(self.agi.database_get('foo', 'bar'), 'foobar')
        self.assertEqual(self.agi.database_get('foo', 'baz'), 'foobaz')
        self.assertEqual(self.agi.database_get('foo', 'bat'), 'foobat')
        self.assertRaises(AGIDBError, self.agi.database_get, 'foo', 'foo')
        self.agi.database_del('foo', 'bar')
        self.assertRaises(AGIDBError, self.agi.database_del, 'foo', 'bar')
        self.agi.database_deltree('foo')
        self.assertRaises(AGIDBError, self.agi.database_deltree, 'foo')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest (unittest.makeSuite (Test_Manager))
    suite.addTest (unittest.makeSuite (Test_AGI))
    return suite

if __name__ == '__main__':
    unittest.main()

