#! /usr/bin/env python2.7
# coding: utf-8
# Source Generated with Decompyle++
# File: gnut.pyc (Python 2.0)

'''Gnutella protocol implementation'''
__version__ = 'Ka-Ping Yee, 18 November 2000'
import string
import struct
import random
import md5
import sys
import os
import socket
import select
import time

def nonce():
    seed = '%s-%s-%s' % (random.random(), time.time(), os.getpid())
    return md5.new(seed).digest()


def intify(num):
    
    try:
        return int(num)
    except:
        return num

# def f(c):
#    if 32 < ord(c):
#        passord(c) < 1271

def hexify(data):
    # f = lambda c: if 32 < ord(c): passord(c) < 1271
    f = lambda c: passord(c) < 1271 if 32 < ord(c) else None
    if len(filter(f, data)) == len(data):
        return '"%s"' % data
    
    return '%02x' * len(data) % tuple(map(ord, data))


def atoq(addr):
    parts = map(int, string.split(addr, '.'))
    return apply(struct.pack, ('BBBB',) + tuple(parts))


def qtoa(quad):
    return '%d.%d.%d.%d' % struct.unpack('BBBB', quad)


class Message:
    payload = ''
    
    def __init__(self):
        self.mid = nonce()

    
    def __repr__(self):
        return '<Message %s>' % repr(self.payload)

    
    def header(self, ttl):
        return struct.pack('<16sBBBI', self.mid, self.cmd, ttl, 0, self.size)

    
    def encode(self, ttl):
        return self.header(ttl) + self.payload



class RMessage(Message):
    
    def __init__(self, header):
        (self.mid, self.cmd, self.ttl, self.hops, self.size) = struct.unpack('<16sBBBI', header)

    
    def __repr__(self):
        return '<Message[%d] (%d/%d) %s>' % (self.cmd, self.hops, self.ttl, repr(self.payload))

    
    def age(self):
        self.hops = self.hops + 1
        self.ttl = self.ttl - 1



class Ping(Message):
    cmd = 0
    size = 0
    payload = ''
    
    def __repr__(self):
        return '<Ping>'



class RPing(Ping, RMessage):
    
    def __init__(self, header, payload):
        RMessage.__init__(self, header)

    
    def __repr__(self):
        return '<Ping (%d/%d)>' % (self.hops, self.ttl + self.hops)



class Pong(Message):
    cmd = 1
    size = 14
    
    def __init__(self, host, port, files, kb):
        Message.__init__(self)
        self.host = host
        self.addr = socket.gethostbyname(host)
        self.port = port
        self.files = files
        self.kb = kb
        self.payload = struct.pack('<H4sII', port, atoq(self.addr), files, kb)

    
    def __repr__(self):
        return '<Pong %s:%s - %s f, %s kb>' % (self.addr, self.port, self.files, self.kb)



class RPong(Pong, RMessage):
    
    def __init__(self, header, payload):
        (port, quad, files, kb) = struct.unpack('<H4sII', payload)
        files = intify(files)
        kb = intify(kb)
        Pong.__init__(self, qtoa(quad), port, files, kb)
        RMessage.__init__(self, header)

    
    def __repr__(self):
        return '<Pong (%d/%d) %s:%s - %s f, %s kb>' % (self.hops, self.ttl + self.hops, self.addr, self.port, self.files, self.kb)



class Query(Message):
    cmd = 128
    
    def __init__(self, key, speed):
        Message.__init__(self)
        self.key = key
        self.speed = speed
        self.payload = struct.pack('<H', speed) + key + '\x00'
        self.size = len(self.payload)

    
    def __repr__(self):
        speed = ''
        if self.speed:
            speed = ' (speed >= %d)' % self.speed
        
        return '<Query %s%s>' % (repr(self.key), speed)



class RQuery(Query, RMessage):
    
    def __init__(self, header, payload):
        if len(payload) < 2:
            payload = '\x00\x00'
        
        (speed,) = struct.unpack('<H', payload[:2])
        key = payload[2:-1]
        Query.__init__(self, key, speed)
        RMessage.__init__(self, header)

    
    def __repr__(self):
        speed = ''
        if self.speed:
            speed = ' (speed >= %d)' % self.speed
        
        return '<Query (%d/%d) %s%s>' % (self.hops, self.ttl + self.hops, repr(self.key), speed)



class Hits(Message):
    cmd = 129
    
    def __init__(self, id, host, port, speed, hits):
        Message.__init__(self)
        self.id = id
        self.host = host
        self.addr = socket.gethostbyname(host)
        self.port = port
        self.speed = speed
        self.hits = hits
        self.payload = struct.pack('<Bh4sI', len(hits), port, atoq(self.addr), speed)
        for (index, size, name) in hits:
            self.payload = self.payload + struct.pack('<II', index, size) + name + '\x00\x00'
        
        self.payload = self.payload + id
        self.size = len(self.payload)

    
    def __repr__(self):
        return '<Hits [%s] %s:%s - %s found (speed %s)>' % (hexify(self.id), self.addr, self.port, len(self.hits), self.speed)



class RHits(Hits, RMessage):
    
    def __init__(self, header, payload):
        (count, port, quad, speed) = struct.unpack('<BH4sI', payload[:11])
        speed = intify(speed)
        hits = []
        results = payload[11:]
        for i in range(count):
            (index, size) = struct.unpack('<II', results[:8])
            index = intify(index)
            size = intify(size)
            end = string.find(results, '\x00\x00', 8)
            (name, results) = (results[8:end], results[end + 2:])
            hits.append((index, size, name))
        
        id = results
        Hits.__init__(self, id, qtoa(quad), port, speed, hits)
        RMessage.__init__(self, header)

    
    def __repr__(self):
        return '<Hits (%d/%d) [%s] %s:%s - %s found (speed %s)>' % (self.hops, self.ttl + self.hops, hexify(self.id), self.addr, self.port, len(self.hits), self.speed)



class Push(Message):
    cmd = 64
    size = 26
    
    def __init__(self, id, index, host, port):
        Message.__init__(self)
        self.id = id
        self.index = index
        self.host = host
        self.addr = socket.gethostbyname(host)
        self.port = port
        self.payload = struct.pack('<16sI4sH', id, index, atoq(self.addr), port)

    
    def __repr__(self):
        return '<Push [%s] %s to %s:%s>' % (hexify(self.id), self.index, self.addr, self.port)



class RPush(Push, RMessage):
    
    def __init__(self, header, payload):
        (id, index, quad, port) = struct.unpack('<16sI4sH', payload)
        index = intify(index)
        Push.__init__(self, id, index, qtoa(quad), port)
        RMessage.__init__(self, header)

    
    def __repr__(self):
        return '<Push (%d/%d) [%s] %s to %s:%s>' % (self.hops, self.ttl + self.hops, hexify(self.id), self.index, self.addr, self.port)


rclass = { }
for cl in (RPing, RPong, RQuery, RHits, RPush):
    rclass[cl.cmd] = cl


class Conn:
    ttl = 5
    
    def __init__(self, host, port=6346, open=1):
        self.host = host
        self.port = port
        self.connected = 0
        if open:
            self.open()
        
        self.inselect = 0
        self.incollect = 0

    
    def __repr__(self):
        if not (self.connected):
            return '<Conn (unopened) to %s:%d>' % (self.host, self.port)
        
        return '<Conn to %s:%d>' % (self.addr, self.port)

    
    def open(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = socket.gethostbyname(self.host)
        s.connect((self.addr, self.port))
        self.rfile = s.makefile('rb', 0)
        self.wfile = s.makefile('wb', 0)
        self.connected = 1
        self.wfile.write('GNUTELLA CONNECT/0.4\n\n')
        if self.rfile.readline() != 'GNUTELLA OK\n':
            raise IOError, 'login failed'
        
        self.rfile.readline()

    
    def close(self):
        self.rfile.close()
        self.wfile.close()
        self.connected = 0

    
    def send(self, message, ttl=None):
        if ttl is None and hasattr(message, 'ttl'):
            ttl = message.ttl
        
        if ttl is None:
            ttl = self.ttl
        
        
        try:
            self.wfile.write(message.encode(ttl))
        except (socket.error, IOError):
            print 'closing on send error', self
            self.error = sys.exc_info()
            self.close()


    
    def recv(self):
        
        try:
            header = self.rfile.read(23)
        except (socket.error, IOError):
            self.error = sys.exc_info()
            header = None

        if not header:
            print 'closing on recv error', self
            self.close()
            return None
        
        rmsg = RMessage(header)
        
        try:
            payload = self.rfile.read(rmsg.size)
        except (socket.error, IOError):
            self.error = sys.exc_info()
            print 'closing on incomplete message', self
            self.close()
            return None

        if rclass.has_key(rmsg.cmd):
            return rclass[rmsg.cmd](header, payload)
        else:
            rmsg.payload = payload
            return rmsg

    
    def fileno(self):
        return self.rfile.fileno()

    
    def ping(self, ttl=None):
        msg = Ping()
        self.send(msg, ttl)
        return msg

    
    def query(self, key, speed=0, ttl=None):
        msg = Query(key, speed)
        self.send(msg, ttl)
        return msg

    
    def dump(self, types=[
        Message], filter=None, timeout=10, max=20):
        i = 0
        alarm = time.time() + timeout
        while i < max:
            (rfd, wfd, efd) = select.select([
                self.rfile.fileno()], [], [], timeout)
            if not rfd or time.time() > alarm:
                break
            
            msg = self.recv()
            if msg is None:
                break
            
            for t in types:
                if isinstance(msg, t):
                    if filter and not filter(msg):
                        continue
                    
                    alarm = time.time() + timeout
                    i = i + 1
                    print msg
                    if isinstance(msg, Hits):
                        print msg.hits
                    
                    break
                
            
            continue
            0

    
    def collect(self, types=[
        Message], filter=None, timeout=10, max=20):
        self.incollect = 1
        results = []
        alarm = time.time() + timeout
        while len(results) < max:
            self.inselect = timeout
            (rfd, wfd, efd) = select.select([
                self.rfile.fileno()], [], [], timeout)
            self.inselect = 0
            if not rfd or time.time() > alarm:
                break
            
            msg = self.recv()
            if msg is None:
                break
            
            for t in types:
                if isinstance(msg, t):
                    if filter and not filter(msg):
                        continue
                    
                    alarm = time.time() + timeout
                    results.append(msg)
                    break
                
            
            continue
            0
        self.incollect = 0
        return results



try:
    import threading
except ImportError:
    0
    (RPing, RPong, RQuery, RHits, RPush)
except:
    0


class ThrConn(threading.Thread, Conn):
    
    def __init__(self, host, port=6346):
        threading.Thread.__init__(self)
        Conn.__init__(self, host, port, open=0)
        self.messages = []
        self.events = []
        self.error = None
        self.closing = 0
        self.lock = threading.Lock()
        self.loopcount = 0
        self.looping = 0
        self.opening = 0

    
    def __repr__(self):
        return '<ThrConn' + Conn.__repr__(self)[5:]

    
    def run(self):
        
        try:
            self.opening = 1
            self.open()
            self.opening = 0
        except (IOError, socket.error):
            self.error = sys.exc_info()
            self.opening = 0
            return None

        while self.connected:
            self.looping = 0
            results = self.collect(timeout=1, max=10)
            self.looping = 1
            self.loopcount = self.loopcount + 1
            if results:
                for event in self.events:
                    event.set()
                
            
            self.lock.acquire()
            self.messages[len(self.messages):] = results
            self.lock.release()
            if self.closing:
                print 'closing on request', self
                Conn.close(self)
            

    
    def get(self, max=None):
        self.lock.acquire()
        if max:
            results = self.messages[:max]
            self.messages[:max] = []
        else:
            results = self.messages[:]
            self.messages[:] = []
        self.lock.release()
        return results

    
    def notify(self, event):
        self.events.append(event)

    
    def close(self):
        self.closing = 1
