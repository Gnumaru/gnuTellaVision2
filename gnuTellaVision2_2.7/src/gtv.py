#! /usr/bin/env python2.7
# coding: utf-8
import Tkinter
import math
import os
import socket
import string
import sys
import threading
import time

import gnut
from host import DeleteLine, Host, Line, MakeLine, cx, cy, rs, polar
import host


host.TF = TF = 1

TESTKEY = 'UC Berkeley test %d' % os.getpid()
MAXTHREADS = 20
nthreads = 0
timestep = 100

win = Tkinter.Tk()
win.title('Gnutella')
win.wm_geometry('+0+0')
canvas = Tkinter.Canvas(win, width=600, height=600, bg='white')
canvas.pack()

event = threading.Event()

#addr = socket.gethostbyname('gnutellahosts.com')
addr = socket.gethostbyname('50.11.240.185')
top = Host(canvas, addr, 0)
top.kb = 0
#top.port = 6346
top.port = 49722
hosts = {addr: top}
workqueue = []

status = canvas.create_text(10, 0, font=('helvetica', 10),
                            anchor='nw', fill='white')
info = canvas.create_text(300, 599, font=('helvetica', 16),
                          anchor='s', justify='center')
queries = canvas.create_text(5, 599, font=('helvetica', 12),
                             anchor='sw', fill='grey')
canvas.lower(queries)
querylist = ['']

circles = []
fading = ['#ffd0d0', '#ffd8d8', '#ffe0e0', '#ffe8e8', '#fff0f0', '#fff8f8']
for r in range(10):
    rr = rs * r
    c = canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                           outline='#ff%02x%02x' % (0xd0 + 4 * r, 0xd0 + 4 * r))
    canvas.lower(c)
    circles.append(c)

moves = 0
def hover(event):
    global moves

    canvas = event.widget
    ids = canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
    for id in ids:
        host = Host.ovaltohost.get(canvas.items.get(id))
        if host:
            time.sleep(TF * 0.1)
            text = '%s:%s (%s files)' % (
                host.addr, host.port, host.files)
            if hasattr(host, 'kb'):
                other = host.counts.get('other', 0)
                pong = host.counts.get('pong', 0)
                query = host.counts.get('query', 0)
                text = '%s:%s (%s files, %s kb)\n' % (
                    host.addr, host.port, host.files, host.kb) + \
                    '%d messages (%d queries, %d pongs)' % (
                    other + pong + query, query, pong)
            canvas.itemconfig(info, text=text)
            canvas.tkraise(info)
            host.flash('pink')
            moves = 5
            break
    else:
        if moves > 0:
            moves = moves - 1
            if moves == 0:
                canvas.itemconfig(info, text='')
                canvas.tkraise(info)

def click(event):
    canvas = event.widget
    ids = canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
    for id in ids:
        host = Host.ovaltohost.get(canvas.items.get(id))
        if host:
            try: host.conn.query(TESTKEY, ttl=2)
            except (IOError, AttributeError): pass
            time.sleep(TF * 0.1)
            host.flash('red')
            break

def middleclick(event):
    # print 'middleclick'
    canvas = event.widget
    ids = canvas.find_overlapping(event.x - 2, event.y - 2, event.x + 2, event.y + 2)
    for id in ids:
        host = Host.ovaltohost.get(canvas.items.get(id))
        if host:
            global newcenter
            # print 'newcenter', host
            newcenter = host
            time.sleep(TF * 0.1)
            host.oval.config(fill='purple')
            break

newcenter = None

def arg((ox, oy), (dx, dy), min=0):
    angle = math.atan2(dy - oy, dx - ox) * 180.0 / math.pi
    angle = angle % 360.0
    while angle < min: angle = angle + 360.0
    while angle >= min + 360.0: angle = angle - 360.0
    return angle

def recenter(newtop):
    # print 'recenter', newtop
    if not newtop.parent:
        newtop.setstate(newtop.state)
        return

    # print 'center on', newtop
    # print 'my parent is', newtop.parent
    # print 'my angle is', newtop.angle

    time.sleep(TF * 0.1)
    x, y = newtop.xy()
    px, py = newtop.parent.xy()
    # print 'diff', px - x, py - y
    startangle = arg((x, y), (px, py))
    # print 'startangle', startangle

    allhosts = {}
    newchildren = {}
    newqueue = [newtop]
    while newqueue:
        node = newqueue.pop(0)
        if newchildren.has_key(node): continue
        children = []
        examine = [node.parent] + node.children + node.neighbours.keys()
        for child in examine:
            if not newchildren.has_key(child) and child not in newqueue:
                if child:
                    children.append(child)
                    newqueue.append(child)
        newchildren[node] = children
    allhosts = newchildren.keys()
    xy = {}
    ra = {}
    for host in allhosts:
        xy[host] = host.xy()
        ra[host] = host.radius, host.angle

    for host in allhosts:
        children = newchildren[host]
        angles = {}
        if host.parent:
            parentangle = arg(xy[host], xy[host.parent])
            # print 'my parent', host.parent.addr
        else:
            parentangle = arg(xy[host], xy[newtop])
            # print 'new top', newtop.addr
        # print 'i am', host.addr
        # print 'my parentangle', parentangle
        for child in children:
            angles[child] = arg(xy[host], xy[child], parentangle)
        def cmpangle(a, b, angles=angles):
            return cmp(angles[a], angles[b])
        children.sort(cmpangle)
        # print 'children:', map(lambda x: x.addr, children)
        # print 'children:', map(lambda x, angles=angles: angles[x], children)

        for child in children:
            if child.branch:
                DeleteLine(child.branch.origin, child.branch.dest)
                child.branch = None
            if child.parent: child.join(child.parent)
            child.parent = host
            child.split(host)
            child.branch = MakeLine(child, host, Host.DIRECT_LINE)
        host.children = children
    global top
    top = newtop
    top.parent = None
    top.move(0.0, startangle, startangle + 360.0)
    # print 'my first child is', top.children[0]
    # print 'its angle is', top.children[0].angle
    diff = top.children[0].angle - startangle
    # print 'off by', diff
    startangle = (startangle - diff) % 360.0
    top.move(0.0, startangle, startangle + 360.0)
    # print 'my first child is', top.children[0]
    # print 'its angle is', top.children[0].angle

    coords = []
    for host in allhosts:
        # coords.append((host,) + xy[host] + host.xy())
        r, a = ra[host]
        nr, na = host.radius, host.angle
        if r == 0: a = na
        if nr == 0: na = a
        da = (na - a) % 360
        if da > 180: da = da - 360
        coords.append((host, r, a, nr, a + da))

    lines = {}
    for line in Line.lines.values():
        lines[line] = 1

    for step in range(50):
        new = math.atan((step / 50.0) * 10 - 5) * 0.5 / math.atan(5) + 0.5
        old = 1.0 - new
        for host, r, a, nr, na in coords:
            apply(host.movexy, polar(old * r + new * nr, old * a + new * na))
            # host.movexy(old*x + new*nx, old*y + new*ny)
        for line in lines.keys():
            line.update()
        canvas.update()
        time.sleep(TF * 0.05)
    newtop.setstate(newtop.state)

def showthreads():
    canvas.itemconfig(status, text='(%d) %d/%d' % 
        (len(threading.enumerate()) - 1, nthreads, MAXTHREADS))

def check():
    global newcenter, nthreads
    showthreads()

    while workqueue and nthreads < MAXTHREADS:
        (src, host, port) = workqueue.pop(0)
        conn = gnut.ThrConn(host, port)
        try:
            conn.setDaemon(1)
            conn.start()
        except:
            # print 'threading error', sys.exc_info()
            workqueue.insert(0, (src, host, port))
            # print 'think', nthreads
            # nthreads = len(threading.enumerate()) - 1
            # print 'actual', nthreads
            # print 'threads:', threading.enumerate()
            break
        # nthreads = nthreads + 1
        src.attempttime = time.time()
        src.init(conn)
        # print 'spawn', src
    canvas.update()

    for host in hosts.values():
        if host.state in (Host.DROPPED, Host.REFUSED): continue
        if newcenter: break

        if host.conn and host.conn.messages:
            for msg in host.conn.messages:
                if isinstance(msg, gnut.Query) and msg.key == TESTKEY:
                    host.flash('red')
                    canvas.itemconfig(info, text=
                        'query echo from %s' % host.addr)
                    canvas.tkraise(info)
            if host.conn.isAlive():
                messages = host.conn.get(1)
            else:
                messages = filter(lambda msg: isinstance(msg, gnut.Pong),
                                  host.conn.get())[:10]
                host.conn.messages = []
                                  
            if messages:
                for msg in messages:
                    if isinstance(msg, gnut.Pong):
                        host.count('pong')
                        if msg.addr in ['127.0.0.1', '0.0.0.0']: continue
                        src = hosts.get(msg.addr)
                        if src:
                            src.resize(msg.files)
                            src.join(host)
                        else:
                            src = Host(canvas, msg.addr, msg.files, host)
                            src.kb = msg.kb
                            src.port = msg.port
                            top.arrange()
                            hosts[msg.addr] = src
                            workqueue.append((src, msg.addr, msg.port))
                    elif isinstance(msg, gnut.Query):
                        host.count('query')
                        if msg.key == TESTKEY:
                            host.flash('red')
                            canvas.itemconfig(info, text=
                                'query echo from %s' % host.addr)
                            canvas.tkraise(info)
                        host.gotquery(msg.key)
                        if msg.key and 32 <= ord(msg.key[0]) < 127:
                            key = string.join(string.split(msg.key, '\x00'), '')
                            querylist.append(key)
                            text = string.join(querylist[-60:], '\n')
                            canvas.itemconfig(queries, text=text)
                    else:
                        host.count('other')
                canvas.update()
                time.sleep(TF * 0.05)

        if host.state == Host.CONNECTING:
            if host.conn.connected:
                nthreads = nthreads + 1
                showthreads()
                host.connecttime = time.time()
                host.connect()
                try: host.conn.ping(ttl=2)
                except IOError: pass

        if host.conn and not host.conn.isAlive() and not host.conn.messages:
            # print 'terminated', host
            if host.state == Host.CONNECTED:
                host.drop()
            elif host.conn.error:
                errmsg = string.lower(host.conn.error[1].args[-1])
                if host.state == Host.CONNECTING:
                    if string.find(errmsg, 'refused') >= 0:
                        host.refuse()
                    else:
                        host.delete()
                        del hosts[host.conn.host]
            nthreads = nthreads - 1

    if nthreads > MAXTHREADS - 5:
        def cmptime(a, b, now=time.time()):
            at = a.__dict__.get('attempttime', now)
            bt = a.__dict__.get('attempttime', now)
            return cmp(at, bt)

        h = filter(lambda h: h.conn and h.conn.isAlive() and
                             not h.conn.opening and not h.conn.closing,
                   hosts.values())
        h.sort(cmptime)
        for old in h[:nthreads - (MAXTHREADS - 5)]:
            print 'killing off', old, old.conn.incollect, old.conn.inselect, \
                old.conn.looping, old.conn.loopcount, old.conn.opening
            old.conn.close()

    if newcenter:
        recenter(newcenter)
        newcenter = None

    lock = 0
    canvas.tk.createtimerhandler(timestep * TF, check)

canvas.bind("<Button-1>", click, '+')
canvas.bind("<Shift-Button-1>", middleclick, '+')
canvas.bind("<Button-3>", hover, '+')
canvas.tk.createtimerhandler(timestep * TF, check)
canvas.tk.createtimerhandler(1000, lambda *args: workqueue.append((top, addr, 6346)))
Tkinter.mainloop()
