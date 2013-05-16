"""
This module provides a Supervisor 'event handler' conforming to the interface
at http://supervisord.org/events.html.  To use it, add a section like this to
your Supervisor configuration:

[eventlistener:proc_publisher]
command=proc_publisher
events=PROCESS_STATE,PROCESS_GROUP,TICK_60
environment=REDIS_URL="redis://localhost:6379/0"

You should *not* configure a stdout_logfile for this program (it messes up the
communication with Supervisor).

For each PROCESS_STATE and PROCESS_GROUP message received, the publisher will
put a json-encoded dict on the Redis pubsub specified in the eventlistener's
environment variables.  Velociraptor web procs will listen on this pubsub for
proc state changes and update dashboards in realtime.

The listener will also maintain a cache of the host's proc data in a Redis
hash.  This cache will be updated whenever an event is received from
Supervisor.  By configuring the eventlistener to receive TICK_60 events, the
cache will be updated once per minute, even if no process state changes have
occurred.
"""

import os
import sys
import json
import datetime
import socket

import redis

from raptor.utils import parse_redis_url
from raptor.models import Host, Proc
from raptor import supervisor_utils


def main():
    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        raise SystemExit('supervisor_events_publisher must be run as a '
                         'supervisor event listener')

    # Use Supervisor's own RPC interface to get full proc data on each process
    # state change, since the emitted events don't have everything we want.
    rpc = supervisor_utils.getRPCInterface(os.environ)

    rcon = redis.StrictRedis(**parse_redis_url(os.environ['REDIS_URL']))
    hostname = os.getenv('HOSTNAME', socket.getfqdn())
    log('proc_publisher starting with hostname %s' % hostname)
    log('connecting to redis at %s' % os.environ['REDIS_URL'])
    host = Host(hostname, rpc_or_port=rpc, redis_or_url=rcon,)

    for e in EventStream(hostname):
        handle_event(e, host, 'proc_events')
        log(e.emit())


def handle_event(event, host, pubsub_channel):
    data = event.emit()
    if event.eventname.startswith('PROCESS_STATE'):
        proc_name = data['payload_headers']['processname']
        proc_data = host.get_proc(proc_name, check_cache=False).as_dict()

        # Include event type with all messages so listeners can ignore messages
        # they don't care about.
        proc_data.update(event=event.eventname)
        host.redis.publish(pubsub_channel, json.dumps(proc_data))

    elif event.eventname == 'PROCESS_GROUP_REMOVED':
        # Supervisor's events interface likes to call things 'process' or
        # 'group' or 'processname', but the xmlrpc interface gives
        # processes a 'name' and 'group'.  Velociraptor likes to use
        # 'name'.
        data['name'] = data['payload_headers']['groupname']
        # Parse out the bits of the name
        data.update(Proc.parse_name(data['name']))
        # also add in the 'id' field that procs have, since the dashboard will
        # rely on that to pluck out the JS proc model
        data['id'] = '%s-%s' % (host.name, data['name'])
        host.redis.publish(pubsub_channel, json.dumps(data))

    # No matter what kind of event we got, update the host's whole cache.
    host.get_procs(check_cache=False)


class Event(object):

    def __init__(self, headers, payload, hostname):
        # Save the raw data
        self.headers = headers
        self.payload = payload

        self.host = hostname

        # Parse out some useful bits
        self.eventname = headers['eventname']
        self.payload_headers, self.payload_data = supervisor_utils.eventdata(payload
                                                                       + '\n')
        if 'when' in self.payload_headers:
            utime = float(self.payload_headers['when'])
            self.time = datetime.datetime.utcfromtimestamp(utime)
        else:
            self.time = datetime.datetime.utcnow()

    def emit(self):
        data = {
            'event': self.eventname,
            'host': self.host,
            'payload_headers': self.payload_headers,
            'payload_data': self.payload_data,
            'time': self.time.isoformat(),
        }
        return data

    def __repr__(self):
        return '<Event %s>' % self.eventname


class EventStream(object):
    """
    Iterator over Supervisor-emitted events.

        es = EventStream()
        for e in es:
            do_something(e)
    """

    def __init__(self, hostname):
        self.hostname = hostname
        # Makes testing easier
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

        # Flag for whether an 'ok' is needed at the beginning of the next
        # self.next() call.
        self._needs_ok = False


    def __iter__(self):
        while 1:
            yield self.next()

    def next(self):
        if self._needs_ok:
            supervisor_utils.listener.ok(self.stdout)

        headers, payload = supervisor_utils.listener.wait(self.stdin, self.stdout)
        self._needs_ok = True
        return Event(headers, payload, self.hostname)


def log(*args):
    """
    Since the Supervisor event listener spec attaches special meaning to
    stdout, we can't use normal print.  Use this instead to print to
    stderr.
    """
    for s in args:
        sys.stderr.write(str(s) + '\n')
    sys.stderr.flush()

