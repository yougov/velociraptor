"""
This module provides a Supervisor 'event handler' conforming to the interface
at http://supervisord.org/events.html.  To use it, add a section like this to
your Supervisor configuration:

[eventlistener:proc_publisher]
command=proc_publisher
events=PROCESS_STATE,PROCESS_GROUP
environment=REDIS_URL="redis://localhost:6379/0"

You should *not* configure a stdout_logfile for this program (it messes up the
communication with Supervisor).

For each message received, the publisher will put a json-encoded dict on the
Redis pubsub specified in the eventlistener's environment variables.
Velociraptor web procs will listen on this pubsub for proc state changes and
update dashboards in realtime.
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

def publish_procstatus():
    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        raise SystemExit('supervisor_events_publisher must be run as a '
                         'supervisor event listener')

    # Get config from env vars
    pubsub_channel = os.getenv('PROC_EVENTS_CHANNEL', 'proc_events')
    cache_prefix = os.getenv('PROC_CACHE_PREFIX', 'host_procs_')
    # Make the cached values live for 10 minutes by default.
    cache_lifetime = int(os.getenv('PROC_CACHE_LIFETIME', 600))

    # Use Supervisor's own RPC interface to get full proc data on each process
    # state change, since 
    rpc = childutils.getRPCInterface(os.environ)

    con = redis.StrictRedis(**parse_redis_url(os.environ['REDIS_URL']))
    events = EventStream([ProcEvent, ProcGroupEvent, Event],
                         ignore_unmatched=True)
    for e in events:
        data = e.emit()
        # The cache is saved with one hash per host.  The keys in this hash are
        # proc names, and the values are json-encoded dicts
        cache_key = cache_prefix + data['host']
        if e.eventname.startswith('PROCESS_STATE'):
            proc_data = rpc.supervisor.getProcessInfo(data['process'])
            proc_data['host'] = data['host']
            # TODO: Use caching routine from raptor.models.Host

            # Include host with all messages, as well as event type, so
            # listeners can ignore messages they don't care about.
            proc_data.update(host=data['host'], event=e.eventname)
            serialized = json.dumps(proc_data)
            con.publish(pubsub_channel, serialized)
            con.hset(cache_key, data['process'], serialized)
            con.expire(cache_key, cache_lifetime)

        elif e.eventname == 'PROCESS_GROUP_REMOVED':
            # Supervisor distinguishes between processes and process groups,
            # but Velociraptor doesn't, so replace 'group' with 'process' so
            # listeners can be consistent.
            data['process'] = data.pop('group')
            con.publish(pubsub_channel, json.dumps(data))
            con.hdel(cache_key, data['process'])

        log(e.emit())


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
    def get_data(self):
        """
        Subclasses should override this method to put custom data in the
        payload.  They should not add 'event', 'host', or 'time' fields, as these
        will be added automatically by the emit() function that calls get_data.
        """
        return {
            'payload_headers': self.payload_headers,
            'payload_data': self.payload_data,
        }

    def emit(self):
        data = self.get_data()
        data.update(
            event=self.eventname,
            host=self.host,
        )
        if 'when' in self.payload_headers:
            utime = float(self.payload_headers['when'])
            dt = datetime.datetime.utcfromtimestamp(utime)
            data.update(time=dt.isoformat())
        else:
            data.update(time=datetime.datetime.utcnow().isoformat())

        return data

    def __repr__(self):
        return '<Event %s>' % self.eventname


class ProcEvent(Event):
    pattern = re.compile('^PROCESS_STATE*')

    def __init__(self, *args, **kwargs):
        super(ProcEvent, self).__init__(*args, **kwargs)

        # eventname will be something like PROCESS_STATE_RUNNING.  Split off
        # just the running.
        self.state = self.eventname.rpartition('_')[-1]
        self.previous = self.payload_headers['from_state']
        self.pid = int(self.payload_headers.get('pid', 0))

    def get_data(self):
        data = dict(self.payload_headers)
        data.update(event=self.eventname, host=self.host)
        return {
            'process': self.payload_headers['processname'],
            'state': self.state,
            'previous': self.previous,
            'pid': self.pid,
        }

    def __repr__(self):
        return '<Event %s %s>' % (self.process, self.state)


class ProcGroupEvent(Event):
    pattern = re.compile('^PROCESS_GROUP*')

    def __init__(self, *args, **kwargs):
        super(ProcGroupEvent, self).__init__(*args, **kwargs)

        self.group = self.payload_headers['groupname']

    def __repr__(self):
        return '<Event %s %s>' % (self.eventname, self.groupname)

    def get_data(self):
        return {
            'group': self.group,
        }


class EventStream(object):
    """
    Iterator over Supervisor-emitted events.  Should be initted with a list of
    Event classes and/or subclasses that should be matched to data coming out
    of the stream and then yielded from the iterator.

        es = EventStream(event_classes=(ProcEvent, ProcGroupEvent, Event))

    If the EventStream gets an event on stdin that does not match any of the
    event_classes, it will raise a NoMatch exception.  You can override this
    behavior (and silently ignore unmatched messages) by setting
    ignore_unmatched=True on init.
    """

    def __init__(self, event_classes, ignore_unmatched=False):
        self.event_classes = event_classes
        self.ignore_unmatched = ignore_unmatched

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

        # If ignore_unmatched == True, we'll sit in this loop until getting a
        # message we recognize.
        while 1:
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)

            # Find, instantiate, and return the first of our event classes that
            # matches this eventname
            for cls in self.event_classes:
                if re.match(cls.pattern, headers['eventname']):
                    self._needs_ok = True
                    return cls(headers, payload)
            else:
                # We checked all our event classes and none matched this
                # message.
                if self.ignore_unmatched:
                    childutils.listener.ok(self.stdout)
                    continue
                else:
                    raise NoMatch('No event class matches %s' % headers['eventname'])


class NoMatch(Exception):
    pass


def log(*args):
    """
    Since the Supervisor event listener spec attaches special meaning to
    stdout, we can't use normal print.  Use this instead to print to
    stderr.
    """
    for s in args:
        sys.stderr.write(str(s) + '\n')
    sys.stderr.flush()

