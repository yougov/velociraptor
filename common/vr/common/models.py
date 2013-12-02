import json
from datetime import datetime

try:
    import xmlrpc.client as xmlrpc_client
except ImportError:
    import xmlrpclib as xmlrpc_client

import six
import yaml

try:
    import redis
except ImportError:
    pass # optional dependency

from vr.common.utils import utcfromtimestamp, parse_redis_url


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
    Supervisor-managed processes on the host.  Call it with check_cache=True to
    allow fetching proc info from the Redis cache.

    Call host.get_proc('name') to get a Proc object for the process named
    'name'.  Call it with check_cache=True to allow fetching proc info from the
    Redis cache.  If the host has no proc with that name, ProcError will be
    raised.
    """
    def __init__(self, name, rpc_or_port=9001, supervisor_username=None,
                 supervisor_password=None, redis_or_url=None,
                 redis_cache_prefix='host_procs', redis_cache_lifetime=600):
        self.name = name
        self.username = supervisor_username
        self.password = supervisor_password

        # Allow passing in an RPC connection, or a port number for making one
        if isinstance(rpc_or_port, int):
            if self.username:
                self.rpc = xmlrpc_client.Server('http://%s:%s@%s:%s' %
                                            (self.username,self.password, name,
                                             rpc_or_port))
            else:
                self.rpc = xmlrpc_client.Server('http://%s:%s' % (name, rpc_or_port))
        else:
            self.rpc = rpc_or_port
        self.supervisor = self.rpc.supervisor

        if isinstance(redis_or_url, redis.StrictRedis):
            self.redis = redis_or_url
        elif isinstance(redis_or_url, six.string_types):
            self.redis = redis.StrictRedis(**parse_redis_url(redis_or_url))
        else:
            self.redis = None
        self.cache_key = ':'.join([redis_cache_prefix, name])
        self.cache_lifetime = redis_cache_lifetime

    def get_proc(self, name, check_cache=False):
        if check_cache:
            # Note that if self.redis=None, and check_cache=True, an
            # AttributeError will be raised.
            cached_json = self.redis.hget(self.cache_key, name)
            if cached_json:
                return Proc(self, json.loads(cached_json))
            else:
                procs_dict = self._get_and_cache_procs()
        else:
            procs_dict = self._get_and_cache_procs()

        if name in procs_dict:
            return Proc(self, procs_dict[name])
        else:
            raise ProcError('host %s has no proc named %s' % (self.name, name))

    def _get_and_cache_procs(self):
        proc_list = self.supervisor.getAllProcessInfo()
        # getAllProcessInfo returns a list of dicts.  Reshape that into a dict
        # of dicts, keyed by proc name.
        proc_dict = {d['name']: d for d in proc_list}
        if self.redis:
            # Use pipeline to do hash clear, set, and expiration in same redis call
            with self.redis.pipeline() as pipe:

                # First clear all existing data in the hash
                pipe.delete(self.cache_key)
                # Now set all the hash values, dumped to json.
                dumped = {d: json.dumps(proc_dict[d]) for d in proc_dict}
                pipe.hmset(self.cache_key, dumped)
                pipe.expire(self.cache_key, self.cache_lifetime)
                pipe.execute()

        return proc_dict

    def get_procs(self, check_cache=False):
        if check_cache:
            unparsed = self.redis.hgetall(self.cache_key)
            if unparsed:
                all_data = {v: json.loads(v) for v in unparsed.values()}
            else:
                all_data = self._get_and_cache_procs()
        else:
            all_data = self._get_and_cache_procs()

        return [Proc(self, all_data[d]) for d in all_data]

    def shortname(self):
        return self.name.split(".")[0]

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
    # FIXME: I'm kind of an ugly grab bag of information about a proc, some of
    # it used for initial setup, and some of it the details returned by
    # supervisor at runtime.  In the future, I'd like to have just 3 main
    # attributes:
        # 1. A 'ProcData' instance holding all the info used to create the
        # proc.
        # 2. A 'supervisor' thing that just holds exactly what supervisor
        # returns.
        # 3. A 'resources' thing showing how much RAM and CPU this proc is
        # using.
    # The Supervisor RPC plugin in vr.agent supports returning all of this info
    # in one RPC call.  We should refactor this class to use that, and the
    # cache to use that, and the JS frontend to use that structure too.  Not a
    # small job :(

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
        self.now = utcfromtimestamp(data['now']) if data['now'] else None
        self.pid = data['pid']
        self.spawnerr = data['spawnerr']
        self.start_time = utcfromtimestamp(data['start']) if data['start'] else None
        self.state = data['state']
        self.statename = data['statename']
        self.stderr_logfile = data['stderr_logfile']
        self.stdout_logfile = data['stdout_logfile']
        self.stop_time = utcfromtimestamp(data['stop']) if data['stop'] else None

        # The names returned from Supervisor have a bunch of metadata encoded
        # in them (at least until we can get a Supervisor RPC plugin to return
        # it).  Parse that out and set attributes.
        for k, v in self.parse_name(self.name).items():
            setattr(self, k, v)

        # We also set some convenience attributes for JS/CSS. It would be nice
        # to set those in the JS layer, but that takes some hacking on
        # Backbone.
        self.jsname = self.name.replace('.', 'dot')
        self.id = '%s-%s' % (self.host.name, self.name)

    @staticmethod
    def parse_name(name):
        try:
            app_name, version, config_name, rel_hash, proc_name, port = name.split('-')

            return {
                'app_name': app_name,
                'version': version,
                'config_name': config_name,
                'hash': rel_hash,
                'proc_name': proc_name,
                'port': int(port)
            }
        except ValueError:
            return {
                'app_name': name,
                'version': 'UNKNOWN',
                'config_name': 'UNKNOWN',
                'hash': 'UNKNOWN',
                'proc_name': name,
                'port': 0
            }

    @classmethod
    def name_to_shortname(cls, name):
        """
        In Celery tasks you often have a proc name, and want to send events
        including the proc's shortname, but you don't want to do a XML RPC call
        to get a full dict of data just for that.
        """
        return '%(app_name)s-%(version)s-%(proc_name)s' % Proc.parse_name(name)

    def __repr__(self):
        return "<Proc %s>" % self.name

    def shortname(self):
        return '%s-%s-%s' % (self.app_name, self.version, self.proc_name)

    def as_node(self):
        """
        Return host:port, as needed by the balancer interface.
        """
        return '%s:%s' % (self.host.name, self.port)

    def as_dict(self):
        data = {}
        for k, v in self.__dict__.items():
            if isinstance(v, six.string_types + (int,)):
                data[k] = v
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
            elif v is None:
                data[k] = v
        data['host'] = self.host.name
        return data

    def as_json(self):
        return json.dumps(self.as_dict())

    def start(self):
        try:
            self.host.supervisor.startProcess(self.name)
        except xmlrpc_client.Fault as f:
            if f.faultString == 'ALREADY_STARTED':
                pass
            else:
                raise

    def stop(self):
        try:
            self.host.supervisor.stopProcess(self.name)
        except xmlrpc_client.Fault as f:
            if f.faultString == 'NOT_RUNNING':
                pass
            else:
                raise

    def restart(self):
        self.stop()
        self.start()


class ProcError(Exception):
    """
    Raised when you request a proc that doesn't exist.
    """
    pass


class ConfigData(object):
    """
    Superclass for defining objects with required and optional attributes that
    are set by passing in a dict on init.

    Subclasses should have '_required' and '_optional' lists of attributes to
    be pulled out of the dict on init.
    """
    def __init__(self, dct):

        # KeyError will be raised if any of these are missing from dct.
        for attr in self._required:
            setattr(self, attr, dct[attr])

        # Any of these that are missing from dct will be set to None.
        for attr in self._optional:
            setattr(self, attr, dct.get(attr))

    def as_yaml(self):
        return yaml.safe_dump(self.as_dict(), default_flow_style=False)

    def as_dict(self):
        attrs = {}
        for attr in self._required:
            attrs[attr] = getattr(self, attr)
        for attr in self._optional:
            attrs[attr] = getattr(self, attr)
        return attrs


class ProcData(ConfigData):
    """
    An object with all the attributes you need to set up a proc on a host.
    """
    _required = [
        'app_name',
        'app_repo_url',
        'app_repo_type',
        'buildpack_url',
        'buildpack_version',
        'config_name',
        'env',
        'host',
        'port',
        'version',
        'release_hash',
        'settings',
        'user',
        'proc_name',
    ]

    _optional = [
        'build_url',
        'group',
        'cmd',
        'image_url',
        'image_name',
        'image_md5',
        'build_md5',
        'volumes',
    ]

    # for compatibility, don't require any config yet
    _optional += _required
    _optional.sort()
    del _required[:]

    def __init__(self, dct):

        super(ProcData, self).__init__(dct)
        if self.proc_name is None and 'proc' in dct:
            # Work around earlier versions of proc.yaml that used a different
            # key for proc_name
            setattr(self, 'proc_name', dct['proc'])

        # One of proc_name or cmd must be provided.
        if self.proc_name is None and self.cmd is None:
            raise ValueError('Must provide either proc_name or cmd')
