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
import re

import redis
from supervisor import childutils

from raptor.utils import parse_redis_url
from raptor.models import Host


def main():
    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        raise SystemExit('supervisor_events_publisher must be run as a '
                         'supervisor event listener')

    # Get config from env vars
    pubsub_channel = os.getenv('PROC_EVENTS_CHANNEL', 'proc_events')
    cache_prefix = os.getenv('PROC_CACHE_PREFIX', 'host_procs_')
    # Make the cached values live for 10 minutes by default.
    cache_lifetime = int(os.getenv('PROC_CACHE_LIFETIME', 600))

    # Use Supervisor's own RPC interface to get full proc data on each process
    # state change, since the emitted events don't have everything we want.
    rpc = childutils.getRPCInterface(os.environ)

    rcon = redis.StrictRedis(**parse_redis_url(os.environ['REDIS_URL']))
    host = Host(socket.getfqdn(), rpc_or_port=rpc, redis_or_url=rcon,
                redis_cache_prefix=cache_prefix,
                redis_cache_lifetime=cache_lifetime)

    for e in EventStream():
        handle_event(e, host, pubsub_channel)
        log(e.emit())


def handle_event(event, host, pubsub_channel):
    data = event.emit()
    if event.eventname.startswith('PROCESS_STATE'):
        proc_name = data['payload_headers']['processname']
        proc_data = host.get_proc(proc_name, check_cache=False)._data

        # Include host with all messages, as well as event type, so
        # listeners can ignore messages they don't care about.
        proc_data.update(host=data['host'], event=event.eventname)
        serialized = json.dumps(proc_data)
        host.redis.publish(pubsub_channel, serialized)

    elif event.eventname == 'PROCESS_GROUP_REMOVED':
        # Supervisor's events interface likes to call things 'process' or
        # 'group' or 'processname', but the xmlrpc interface gives
        # processes a 'name' and 'group'.  Velociraptor likes to use
        # 'name'.
        data['name'] = data['payload_headers']['groupname']
        host.redis.publish(pubsub_channel, json.dumps(data))

    # No matter what kind of event we got, update the host's whole cache.
    host.get_procs(check_cache=False)


class Event(object):

    # Subclasses should define their own more-specific event name patterns.
    pattern = re.compile('.*')

    def __init__(self, headers, payload, time=None):
        # Save the raw data
        self.headers = headers
        self.payload = payload

        self.host = socket.getfqdn()

        # Parse out some useful bits
        self.eventname = headers['eventname']
        self.payload_headers, self.payload_data = childutils.eventdata(payload
                                                                       + '\n')

    def emit(self):
        data = {
            'event': self.eventname,
            'host': self.host,
            'payload_headers': self.payload_headers,
            'payload_data': self.payload_data,
        }
        if 'when' in self.payload_headers:
            utime = float(self.payload_headers['when'])
            dt = datetime.datetime.utcfromtimestamp(utime)
            data.update(time=dt.isoformat())
        else:
            data.update(time=datetime.datetime.utcnow().isoformat())
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

    def __init__(self):
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
            childutils.listener.ok(self.stdout)

        headers, payload = childutils.listener.wait(self.stdin, self.stdout)
        self._needs_ok = True
        return Event(headers, payload)


def log(*args):
    """
    Since the Supervisor event listener spec attaches special meaning to
    stdout, we can't use normal print.  Use this instead to print to
    stderr.
    """
    for s in args:
        sys.stderr.write(str(s) + '\n')
    sys.stderr.flush()

