#!/usr/bin/env python

"""manager.py

Interface for Asterisk Manager

"""

import socket
import threading
import Queue
import re
from select import select
from cStringIO import StringIO
from types import *

EOL = '\r\n'

class ManagerMsg(object): 
    def __init__(self, response):
        self.response = response
        self.data = ''
        self.headers = {}
        #print response.getvalue()
        self.parse(response)
        if not self.headers:
            # Bad app not returning any headers.  Let's fake it
            self.headers['Response'] = 'Generated Header'
            #            'Response:'

    def parse(self, response):
        #print response.getvalue()
        response.seek(0)
        #print response.getvalue()
        data = []
        for line in response.readlines():
            line = line.rstrip()
            if not line: continue
            #print 'LINE: %s' % line
            if line.find(':') > -1:
                item = [x.strip() for x in line.split(':')]
                #print 'ITEM:', item
                if len(item) == 2:
                    self.headers[item[0]] = item[1]
                else:
                    data.append[line]
            else:
                data.append(line)
        self.data = '%s\n' % '\n'.join(data)

    def has_header(self, hname):
        return self.headers.has_key(hname)

    def get_header(self, hname):
        return self.headers[hname]

class Event(object):
    callbacks = {}
    registerlock = threading.Lock()
    def __init__(self, message):
        self.message = message
        if not message.has_header('Event'):
            raise ManagerException('Trying to create event from non event message')
        self.name = message.get_header('Event')

        # get a copy of current registered callbacks
        lock = Event.registerlock
        try:
            lock.acquire()
            self.listeners = Event.callbacks.get(self.name,[])[:]
        finally:
            if lock.locked():
                lock.release()

    def dispatch_events(self):
        for func in self.listeners:
            func(self)
    
    # static method
    def register(eventname, func):
        lock = Event.registerlock
        try:
            lock.acquire()
            callbacks = Event.callbacks.get(eventname, [])
            callbacks.append(func)
            Event.callbacks[eventname] = callbacks
        finally:
            if lock.locked():
                lock.release()
    register = staticmethod(register)


class Manager(object):
    #__slots__ = ['host','port','username','secret']
    def __init__(self, host='localhost', port=5038):
        self.host = host
        self.port = port
        # sock_lock is used to serialize acces to the socket in the case of us
        # issuing a command and wanting to read the immediate response
        self.sock_lock = threading.Lock()
        self.sock = None
        self.sockf = None
        self.connected = 0
        self.response_queue = Queue.Queue()
        self.event_queue = Queue.Queue()
        self.reswaiting = []

    def connect(self, host='', port=0):
        host = host or self.host
        port = port or self.port
        assert type(host) in StringTypes
        port = int(port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host,port))
        rsocks, wsocks, esocks = select([],[self.sock],[],60)
        if not wsocks:
            raise ManagerException('Could not establish connection')
        self.sock.setblocking(0)
        self.connected = 1
        # use this for reading only
        self.sockf = self.sock.makefile()
        self.running = 1
        self.event_thread = t = threading.Thread(target=self.event_loop)
        t.start()
        self.event_dispatch_thread = t = threading.Thread(target=self.event_dispatch)
        t.start()
        # hmmmmmm XXX
        return self.response_queue.get()

    def quit(self):
        self.running = 0

        self.event_queue.put(None)
        for waiter in self.reswaiting:
            self.response_queue.put(None)

        if self.event_thread:
            self.event_thread.join()

        if self.event_dispatch_thread:
            self.event_dispatch_thread.join()

        self.sock.shutdown(2)
        self.sock.close()

    def send_action(self, cdict={}, **kwargs):
        cdict.update(kwargs)
        clist = []
        for item in cdict.items():
            #print item
            item = tuple([str(x) for x in item])
            clist.append('%s: %s' % item)
        clist.append(EOL)
        command = EOL.join(clist)

        rsocks, wsocks, esocks = select([],[self.sock],[],60)
        if not wsocks:
            raise ManagerSocketException('Communication Problem:  self.sock not ready for writing')
        if self.sock.fileno() < 0:
            raise ManagerSocketException('Connection Terminated')
        self.sock_lock.acquire()
        try:
            self.sock.sendall(command)
        finally:
            if self.sock_lock.locked():
                self.sock_lock.release()

        self.reswaiting.insert(0,1)
        response = self.response_queue.get()
        self.reswaiting.pop(0)
        return response

    def login(self, username='', secret=''):
        cdict = {'Action':'Login'}
        cdict['Username'] = username
        cdict['Secret'] = secret
        response = self.send_action(cdict)
        return response

    def _receive_data(self):
        """Read the response from a command.
           This SHOULD be called from a block that is locked
           on self.sock_lock
           self.sock should also be ready for reading
        """
        if not self.sock_lock.locked():
            raise ManagerException('self.sock_lock is not locked')
        if self.sock.fileno() < 0:
            raise ManagerSocketException('Connection Terminated')
        lines = []
        while 1:
            try:
                line = self.sockf.readline()
                lines.append(line)
                if line == EOL:
                    break
            except IOError:
                lines.append(EOL)
                break
        return StringIO(''.join(lines))

    def event_loop(self):
        while 1:
            rsocks, wsocks, esocks = select([self.sock],[],[],.1)
            if not self.running: break
            self.sock_lock.acquire()
            try:
                if rsocks:
                    data = self._receive_data()
                    #print data.getvalue()
                    message = ManagerMsg(data)
                    if message.has_header('Event'):
                        ev = Event(message)
                        self.event_queue.put(ev)
                    elif message.has_header('Response'):
                        self.response_queue.put(message)
                    else:
                        print 'No fucking clue what we got\n%s' % message.data
            finally:
                if self.sock_lock.locked():
                    self.sock_lock.release()

    def event_dispatch(self):
        # event dispatching is serialized in this thread
        while 1:
            ev = self.event_queue.get()
            if not ev:
                # None so quit
                break
            ev.dispatch_events()

class ManagerException(Exception): pass
class ManagerSocketException(ManagerException): pass
