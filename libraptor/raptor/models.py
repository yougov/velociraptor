import xmlrpclib
import json
from datetime import datetime

import isodate
import redis

from raptor.utils import parse_redis_url


class Host(object):
    """
    Abstraction over the per-host Supervisor xmlrpc interface.  This is used in
    the Velociraptor web procs, command line clients, and Supervisor event
    listeners.

    Should be initialized with a hostname and either an existing xmlrpc Server
    connection or a port number to where the RPC service is listening.

    If also initialized with a Redis connection or URL, proc info will be
    cached in Redis.

    Call host.get_procs() to get a list of Proc objects for all
    Supervisor-managed processes on the host.  Call it with use_cache=True to
    allow fetching proc info from the Redis cache.

    Call host.get_proc('name') to get a Proc object for the process named
    'name'.  Call it with use_cache=True to allow fetching proc info from the
    Redis cache.

    """
    def __init__(self, name, rpc_or_port=9001, redis_or_url=None,
                 redis_cache_prefix='host_procs_', redis_cache_lifetime=600):
        self.name = name

        # Allow passing in an RPC connection, or a port number for making one
        if isinstance(rpc_or_port, int):
            self.rpc = xmlrpclib.Server('http://%s:%s' % (name, rpc_or_port))
        else:
            self.rpc = rpc_or_port
        self.supervisor = self.rpc.supervisor

        if isinstance(redis_or_url, redis.StrictRedis):
            self.redis = redis_or_url
        elif isinstance(redis_or_url, basestring):
            self.redis = redis.StrictRedis(**parse_redis_url(redis_or_url))
        else:
            self.redis = None
        self.cache_key = redis_cache_prefix + name
        self.cache_lifetime = redis_cache_lifetime

    def get_proc(self, name, use_cache=False):
        if use_cache:
            # Note that if self.redis=None, and use_cache=True, an
            # AttributeError will be raised.
            raw = self.redis.hget(self.cache_key, name)
            if raw:
                data = json.loads(raw)
            else:
                data = self.supervisor.getProcessInfo(name)
                self.cache_proc(data)
        else:
            data = self.supervisor.getProcessInfo(name)

        return Proc(self, data)

    def get_procs(self, use_cache=False):
        if use_cache:
            unparsed = self.redis.hgetall(self.cache_key)
            if unparsed and unparsed.pop('__full__', None) == '1':

                all_data = [json.loads(v) for v in unparsed.values()]
            else:
                all_data = self.supervisor.getAllProcessInfo()
                self.cache_procs(all_data)
        else:
            all_data = self.supervisor.getAllProcessInfo()

        return [Proc(self, d) for d in all_data]

    def cache_proc(self, data):
        """
        Cache data for a given proc.  Accepts a dictionary like that returned
        from the Supevisor getProcessInfo call, and caches that inside a
        per-host hash, using the proc name as the key, and the data dict as the
        value.
        """

        # Using a pipeline here is not strictly necessary, but it turns 3 round
        # trips into 1
        with self.redis.pipeline() as pipe:

            pipe.hset(self.cache_key, data['name'], json.dumps(data))

            # We don't want to rely on the cache for a get_procs() if it's only
            # been hydrated by a single get_proc.  So set a flag in the hash to
            # indicate that get_procs should call Supervisor.  Use hsetnx so we
            # only set that value if it's not already been set.
            pipe.hsetnx(self.cache_key, '__full__', '0')
            pipe.expire(self.cache_key, self.cache_lifetime)
            pipe.execute()

    def cache_procs(self, data_list):
        """
        Cache all process data for a host.  Accepts a list of dictionaries like
        that returned from the Supervisor getAllProcessInfo call, and caches
        that in a Redis hash keyed by the name of each of the host's processes.
        """
        data = {d['name']: json.dumps(d) for d in data_list}
        data['__full__'] = '1'

        # Use pipeline to do hash set and expiration in same redis call
        with self.redis.pipeline() as pipe:
            pipe.hmset(self.cache_key, data)
            pipe.expire(self.cache_key, self.cache_lifetime)
            pipe.execute()

    def __repr__(self):
        info = {
            'cls': self.__class__.__name__,
            'name': self.name,
        }
        return "<%(cls)s %(name)s>" % info


class Proc(object):
    """
    A representation of a proc running on a host.  Must be initted with the
    hostname and a dict of data structured like the one you get back from
    Supervisor's XML RPC interface.
    """

    def __init__(self, host, data):
        self.host = host
        self._data = data

        # Be explicit, not magical, about which keys we expect from the data
        # and which attributes we set on the object.
        self.description = data['description']
        self.exitstatus = data['exitstatus']
        self.group = data['group']
        self.logfile = data['logfile']
        self.name = data['name']
        # When a timestamp field is inapplicable, Supevisor will put a 0 there
        # instead of a real unix timestamp.
        self.now = datetime.fromtimestamp(data['now']) if data['now'] else None
        self.pid = data['pid']
        self.spawnerr = data['spawnerr']
        self.start = datetime.fromtimestamp(data['start']) if data['start'] else None
        self.state = data['state']
        self.statename = data['statename']
        self.stderr_logfile = data['stderr_logfile']
        self.stdout_logfile = data['stdout_logfile']
        self.stop = datetime.fromtimestamp(data['stop']) if data['stop'] else None

        # The names returned from Supervisor have a bunch of metadata encoded
        # in them (at least until we can get a Supervisor RPC plugin to return
        # it).  Parse that out and set attributes.
        for k, v in self._parse_name().items():
            setattr(self, k, v)

        # We also set some convenience attributes for JS/CSS.  Consider pushing
        # the creation of these out to the JS layer.
        self.jsname = self.name.replace('.', 'dot')
        self.id = '%s-%s' % (self.host.name, self.name)

    def _parse_name(self):
        try:
            app_name, version, recipe_name, rel_hash, proc_name, port = self.name.split('-')

            return {
                'app_name': app_name,
                'version': version,
                'recipe_name': recipe_name,
                'hash': rel_hash,
                'proc_name': proc_name,
                'port': int(port)
            }
        except ValueError:
            return {
                'app_name': '~UNKNOWN',
                'version': 'UNKNOWN',
                'recipe_name': 'UNKNOWN',
                'hash': 'UNKNOWN',
                'proc_name': self.name,
                'port': 0
            }

    def __repr__(self):
        return "<Proc %s>" % self.name

    def shortname(self):
        return '%s-%s' % (self.app_name, self.proc_name)

    def as_node(self):
        """
        Return host:port, as needed by the balancer interface.
        """
        return '%s:%s' % (self.host.name, self.port)

    def as_dict(self):
        data = {}
        for k, v in self.__dict__.items():
            if isinstance(v, (basestring, int)):
                data[k] = v
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
            elif v is None:
                data[k] = v
        data['host'] = self.host.name
        return data
