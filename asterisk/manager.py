#!/usr/bin/env python
# vim: set expandtab shiftwidth=4:

"""
Python Interface for Asterisk Manager

This module provides a Python API for interfacing with the asterisk manager.

   import asterisk.manager
   import sys

   def handle_shutdown(event, manager):
      print "Recieved shutdown event"
      manager.quit()
      # we could analize the event and reconnect here
      
   def handle_event(event, manager):
      print "Recieved event: %s" % event.name
   
   manager = asterisk.manager.Manager()   # optionally pass host to connect to
   
   # connect to the manager
   try:
      manager.connect('host') 
      manager.login('user', 'secret')
   except asterisk.manager.ManagerSocketException, reason:
      print "Error connecting to the manager: %s" % reason
      sys.exit(1)
   except asterisk.manager.ManagerAuthException, reason:
      print "Error logging in to the manager: %s" % reason
      sys.exit(1)

   # register some callbacks
   manager.register_event('Shutdown', handle_shutdown) # shutdown
   manager.register_event('*', handle_event)           # catch all
   
   # get a status report
   response = manager.status()

   # we are done, peace
   manager.logoff()
   manager.quit()

Remember all header, response, and event names are case sensitive.

Not all manager actions are implmented as of yet, feel free to add them
and submit patches.
"""

import sys,os
import socket
import threading
import Queue
import re
from select import select
from cStringIO import StringIO
from types import *
from time import sleep

EOL = '\r\n'

# how much debugging do we want
DEBUG = 0

class ManagerMsg(object): 
    """A manager interface message"""
    def __init__(self, response):
        self.response = response  # the raw response, straight from the horse's mouth
        self.data = ''
        self.headers = {}
        
        # parse the response
        self.parse(response)
        
        if not self.headers:
            # Bad app not returning any headers.  Let's fake it
            # this could also be the inital greeting
            self.headers['Response'] = 'Generated Header'
            #            'Response:'

    def parse(self, response):
        """Parse a manager message"""
        if DEBUG:
            print response.getvalue()
        response.seek(0)

        data = []

        # read the response line by line
        for line in response.readlines():
            line = line.rstrip()  # strip trailing whitespace

            if not line: continue  # don't process if this is not a message

            # locate the ':' in our message, if there is one
            if line.find(':') > -1:
                item = [x.strip() for x in line.split(':',1)]

                # if this is a header
                if len(item) == 2:
                    # store the header
                    self.headers[item[0]] = item[1]
                # otherwise it is just plain data
                else:
                    data.append(line)
            # if there was no ':', then we have data
            else:
                data.append(line)

        # store the data
        self.data = '%s\n' % '\n'.join(data)

    def has_header(self, hname):
        """Check for a header"""
        return self.headers.has_key(hname)

    def get_header(self, hname):
        """Return the specfied header"""
        return self.headers[hname]

    def __getitem__(self, hname):
        """Return the specfied header"""
        return self.headers[hname]
    def __repr__(self):
        return self.headers['Response']


class Event(object):
    """Manager interface Events, __init__ expects and 'Event' message"""
    def __init__(self, message):

        # store all of the event data
        self.message = message
        self.data = message.data
        self.headers = message.headers

        # if this is not an event message we have a problem
        if not message.has_header('Event'):
            raise ManagerException('Trying to create event from non event message')

        # get the event name
        self.name = message.get_header('Event')
    
    def has_header(self, hname):
        """Check for a header"""
        return self.headers.has_key(hname)

    def get_header(self, hname):
        """Return the specfied header"""
        return self.headers[hname]
    
    def __getitem__(self, hname):
        """Return the specfied header"""
        return self.headers[hname]
    
    def __repr__(self):
        return self.headers['Event']

    def get_action_id(self):
        return self.headers.get('ActionID',0000)

class Manager(object):
    #__slots__ = ['host','port','username','secret']
    def __init__(self, host='localhost', port=5038):
        # the host and port to connect to
        self.host = host
        self.port = port

        # sock_lock is used to serialize acces to the socket in the case of us
        # issuing a command and wanting to read the immediate response
        self.sock_lock = threading.Lock()

        self.sock = None     # our socket
        self.connected = threading.Event()
        self.running = threading.Event()
        #self.logged_in = 0   
        
        # our hostname
        self.hostname = socket.gethostname()

        # our queues
        self.message_queue = Queue.Queue()
        self.response_queue = Queue.Queue()
        self.event_queue = Queue.Queue()

        # callbacks for events
        self.event_callbacks = {}

        self.reswaiting = []  # who is waiting for a response

        # sequence stuff
        self._seqlock = threading.Lock()
        self._seq = 0
       
        # some threads
        self.event_thread = threading.Thread(target=self.event_loop)
        self.event_dispatch_thread = threading.Thread(target=self.event_dispatch)
        
        self.event_thread.setDaemon(True)
        self.event_dispatch_thread.setDaemon(True)


    #def __del__(self):
    #    self.quit()

    def next_seq(self):
        """Return the next number in the sequence, this is used for ActionID"""
        self._seqlock.acquire()
        try:
            return self._seq
        finally:
            self._seq += 1
            self._seqlock.release()
        
    def send_action(self, cdict={}, **kwargs):
        """
        Send a command to the manager
        
        If a list is passed to the cdict argument, each item in the list will
        be sent to asterisk under the same header in the following manner:

        cdict = {"Action": "Originate",
                 "Variable": ["var1=value", "var2=value"]}
        send_action(cdict)

        ...

        Action: Originate
        Variable: var1=value
        Variable: var2=value
        """
        
        # fill in our args
        cdict.update(kwargs)

        # set the action id
        if not cdict.has_key('ActionID'): cdict['ActionID'] = '%s-%08x' % (self.hostname, self.next_seq())
        clist = []

        # generate the command
        for key, value in cdict.items():
            if isinstance(value, list):
               for item in value:
                  item = tuple([key, item])
                  clist.append('%s: %s' % item)
            else:
               item = tuple([key, value])
               clist.append('%s: %s' % item)
        clist.append(EOL)
        command = EOL.join(clist)

        # make sure the socket is available for writing
        rsocks, wsocks, esocks = select([],[self.sock],[],60)

        # if our socket is not available for writing, handle it
        if not wsocks:
            raise ManagerSocketException('Communication Problem:  self.sock not ready for writing')
        if self.sock.fileno() < 0:
            raise ManagerSocketException('Connection Terminated')

        # lock the soket and send our command
        try:
            self.sock_lock.acquire()
            self.sock.sendall(command)
        finally:
            # release the lock
            self.sock_lock.release()
        
        self.reswaiting.insert(0,1)
        response = self.response_queue.get()
        self.reswaiting.pop(0)
        return response

    def _receive_data(self):
        """
        Read the response from a command.
        This SHOULD be called from a block that is locked
        on self.sock_lock
        self.sock should also be ready for reading
        """

        # loop while we are sill running and connected
        while self.running.isSet() and self.connected.isSet():
            
            # set up for non-blocking action
            rsocks, wsocks, esocks = select([self.sock],[],[],1)

            lines = []  # this holds the message
            try:
                if DEBUG > 2:
                    sys.stderr.write('*')

                # lock our socket
                self.sock_lock.acquire()

                # if there is data to be read
                if rsocks:
                    if DEBUG > 2:  # debug stuff
                        sys.stderr.write('+')

                    # make sure we are still locked, we should not have to check this
                    if not self.sock_lock.locked():
                        raise ManagerException('self.sock_lock is not locked')

                    # make sure there are no problems with the connection
                    if self.sock.fileno() < 0:
                        raise ManagerSocketException('Connection Terminated')

                    # read a message
                    while self.connected.isSet():
                        line = []
 
                        # read a line, one char at a time 
                        while self.connected.isSet():
                            c = self.sock.recv(1)

                            if not c:  # the other end closed the connection
                                self.sock.shutdown(1)
                                self.sock.close()
                                self.connected.clear()
                                break
                            
                            if DEBUG > 3:
                                sys.stderr.write(repr(c))

                            line.append(c)  # append the character to our line

                            # is this the end of a line?
                            if c == '\n':
                                if DEBUG > 3:
                                    sys.stderr.write('\n')
                                line = ''.join(line)
                                break

                        # if we are no longer connected we probably did not
                        # recieve a full message, don't try to handle it
                        if not self.connected.isSet(): break

                        # make sure our line is a string
                        assert type(line) in StringTypes

                        if DEBUG:
                            print line

                        lines.append(line) # add the line to our message

                        # if the line is our EOL marker we have a complete message
                        if line == EOL:
                            break

                        # check to see if this is the greeting line    
                        if line.find('/') >= 0 and line.find(':') < 0:
                            self.title = line.split('/')[0].strip() # store the title of the manager we are connecting to
                            self.version = line.split('/')[1].strip() # store the version of the manager we are connecting to
                            break

                            # why is this here
                            if DEBUG > 2:
                                sys.stderr.write('.')

                        #sleep(.001)  # waste some time before reading another line

            # just in case there are any problems make sure we handle
            # unlocking and such
            finally:
                # if we have a message append it to our queue
                if lines and self.connected.isSet():
                    self.message_queue.put(StringIO(''.join(lines)))

                if DEBUG > 2:
                    sys.stderr.write('-')

                # release our lock, we are done for now
                self.sock_lock.release()
    
    def register_event(self, event, function):
        """
        Register a callback for the specfied event.
        If a callback function returns True, no more callbacks for that
        event will be executed.
        """

        # get the current value, or an empty list
        # then add our new callback
        current_callbacks = self.event_callbacks.get(event, [])
        current_callbacks.append(function)
        self.event_callbacks[event] = current_callbacks

    def event_loop(self):
        """
        The method for the event thread.
        This actually recieves all types of messages and places them
        in the proper queues.
        """

        # start a thread to recieve data
        t = threading.Thread(target=self._receive_data)
        t.setDaemon(True)
        t.start()

        try:
            # loop getting messages from the queue
            while self.running.isSet():
                # get/wait for messages
                data = self.message_queue.get()

                # if we got None as our message we are done
                if not data:
                    break

                # parse the data
                message = ManagerMsg(data)

                # check if this is an event message
                if message.has_header('Event'):
                    self.event_queue.put(Event(message))
                # check if this is a response
                elif message.has_header('Response'):
                    self.response_queue.put(message)
                # this is an unknown message
                else:
                    print 'No clue what we got\n%s' % message.data
        finally:
            # wait for our data receiving thread to exit
            t.join()
                            

    def event_dispatch(self):
        """This thread is responsible fore dispatching events"""

        # loop dispatching events
        while self.running.isSet():
            # get/wait for an event
            ev = self.event_queue.get()

            # if we got None as an event, we are finished
            if not ev:
                break
            
            # dispatch our events

            # first build a list of the functions to execute
            callbacks = self.event_callbacks.get(ev.name, [])
            callbacks.extend(self.event_callbacks.get('*', []))

            # now execute the functions  
            for callback in callbacks:
               if callback(ev, self):
                  break

    def connect(self, host='', port=0):
        """Connect to the manager interface"""

        if self.connected.isSet():
            raise ManagerException('Already connected to manager')

        # set the host and port
        host = host or self.host
        port = port or self.port

        # make sure host is a string
        assert type(host) in StringTypes

        port = int(port)  # make sure port is an int

        # create our socket and connect
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
           self.sock.connect((host,port))
        except socket.error, (errno, reason):
           raise ManagerSocketException(errno, reason)

        # check if we can write to the socket
        rsocks, wsocks, esocks = select([],[self.sock],[],1)
        if not wsocks:
            raise ManagerException('Could not establish connection')

        self.sock.setblocking(1)  # make this a blocking socket
        #self.sock.settimeout(.5)

        # we are connected and running
        self.connected.set()
        self.running.set()

        # start the event thread
        self.event_thread.start()

        # start the event dispatching thread
        self.event_dispatch_thread.start()

        # get our inital connection response
        return self.response_queue.get()

    def quit(self):
        """Shutdown the connection to the manager"""
        
        # if we are still running, logout
        if self.running.isSet() and self.connected.isSet():
            self.logoff()
         

        if self.running.isSet():
            # put None in the queues to make our threads exit
            self.message_queue.put(None)
            self.event_queue.put(None)

            for waiter in self.reswaiting:
                self.response_queue.put(None)

            # wait for the event thread to exit
            self.event_thread.join()

            # make sure we do not join our self (when quit is called from event handlers)
            if threading.currentThread() != self.event_dispatch_thread:
                # wait for the dispatch thread to exit
                self.event_dispatch_thread.join()
            
        self.running.clear()


    def login(self, username='', secret=''):
        """Login to the manager, throws ManagerAuthException when login falis"""
        if not self.connected.isSet():
            raise ManagerException("Not connected")
           
        cdict = {'Action':'Login'}
        cdict['Username'] = username
        cdict['Secret'] = secret
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        if response.get_header('Response') == 'Error':
           self.connected.clear()
           self.quit()  # clean up
           raise ManagerAuthException(response.get_header('Message'))
        
        return response

    def ping(self):
        """Send a ping action to the manager"""
        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'Ping'}
        response = self.send_action(cdict)

        if not response:
            raise ManagerSocketException("Connection close by remote host")
        
        return response

    def logoff(self):
        """Logoff from the manager"""

        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'Logoff'}
        response = self.send_action(cdict)
        
        # if this is true we were probably successful
        if not response:
            self.running.clear()
        
        return response

    def hangup(self, channel):
        """Hanup the specfied channel"""
    
        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'Hangup'}
        cdict['Channel'] = channel
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def status(self, channel = ''):
        """Get a status message from asterisk"""

        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'Status'}
        cdict['Channel'] = channel
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def redirect(self, channel, exten, priority='1', extra_channel='', context=''):
        """Redirect a channel"""
    
        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'Redirect'}
        cdict['Channel'] = channel
        cdict['Exten'] = exten
        cdict['Priority'] = priority
        if context:   cdict['Context']  = context
        if extra_channel: cdict['ExtraChannel'] = extra_channel
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def originate(self, channel, exten, context='', priority='', timeout='', caller_id='', async=False, account='', variables={}):
        """Originate a call"""

        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'Originate'}
        cdict['Channel'] = channel
        cdict['Exten'] = exten
        if context:   cdict['Context']  = context
        if priority:  cdict['Priority'] = priority
        if timeout:   cdict['Timeout']  = timeout
        if caller_id: cdict['CallerID'] = caller_id
        if async:     cdict['Async']    = 'yes'
        if account:   cdict['Account']  = account
        # join dict of vairables together in a string in the form of 'key=val|key=val'
        # with the latest CVS HEAD this is no longer necessary
        # if variables: cdict['Variable'] = '|'.join(['='.join((str(key), str(value))) for key, value in variables.items()])
        if variables: cdict['Variable'] = ['='.join((str(key), str(value))) for key, value in variables.items()]
              
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def mailbox_status(self, mailbox):
        """Get the status of the specfied mailbox"""
     
        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'MailboxStatus'}
        cdict['Mailbox'] = mailbox
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def command(self, command):
        """Execute a command"""

        if not self.connected.isSet():
            raise ManagerException("Not connected")

        cdict = {'Action':'Command'}
        cdict['Command'] = command
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def extension_state(self, exten, context):
        """Get the state of an extension"""

        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'ExtensionState'}
        cdict['Exten'] = exten
        cdict['Context'] = context
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def absolute_timeout(self, channel, timeout):
        """Set an absolute timeout on a channel"""
        
        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'AbsoluteTimeout'}
        cdict['Channel'] = channel
        cdict['Timeout'] = timeout
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

    def mailbox_count(self, mailbox):
        if not self.connected.isSet():
            raise ManagerException("Not connected")
        cdict = {'Action':'MailboxCount'}
        cdict['Mailbox'] = mailbox
        response = self.send_action(cdict)
        
        if not response:
            raise ManagerSocketException("Connection close by remote host")

        return response

class ManagerException(Exception): pass
class ManagerSocketException(ManagerException): pass
class ManagerAuthException(ManagerException): pass


if __name__=='__main__':
    from pprint import pprint

    # our call back function
    def spew(event, mgr):
        print 'EVENT: ', event.name
        pprint(event.headers)
        pprint(event.data)

    # our manager interface
    mgr = Manager('myastbox')
    mgr.register_event('*', spew)  # register a catch all event function

    # connect to the manager
    mess = mgr.connect()
    pprint(mess.headers)
    pprint(mess.data)
   
    # send our auth data
    mess = mgr.login('username','passwd')
    pprint(mess.headers)
    pprint(mess.data)

    try:
        #raw_input("Press <enter> to exit")
        while 1:
            sleep(5)
            os.system('clear')
            mess = mgr.status()
            pprint(mess.headers)
            pprint(mess.data)
    finally:
        mgr.quit()
