import getpass
import re
import socket
import os
import collections
import logging
import copy
import functools
import json

from datetime import datetime
from collections import Iterable
from urlparse import urlparse, parse_qs

try:
    import xmlrpc.client as xmlrpc_client
except ImportError:
    import xmlrpclib as xmlrpc_client

import six
import yaml
import requests
import sseclient

try:
    import redis
except ImportError:
    # optional dependency
    pass

try:
    import keyring
except ImportError:
    # stub out keyring
    class keyring:
        @staticmethod
        def get_password(*args, **kwargs):
            return None

from vr.common.utils import utcfromtimestamp, parse_redis_url

log = logging.getLogger(__name__)


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
                leader = 'http://{self.username}:{self.password}@'
            else:
                leader = 'http://'
            tmpl = leader + '{name}:{port}'
            url = tmpl.format(self=self, name=name, port=rpc_or_port)
            self.rpc = xmlrpc_client.Server(url)
        else:
            self.rpc = rpc_or_port
        self.supervisor = self.rpc.supervisor

        self.redis = self._init_redis(redis_or_url)
        self.cache_key = ':'.join([redis_cache_prefix, name])
        self.cache_lifetime = redis_cache_lifetime

    @staticmethod
    def _init_redis(redis_spec):
        """
        Return a StrictRedis instance or None based on redis_spec.

        redis_spec may be None, a Redis URL, or a StrictRedis instance
        """
        if not redis_spec:
            return
        if isinstance(redis_spec, six.string_types):
            redis_params = parse_redis_url(redis_spec)
            return redis.StrictRedis(**redis_params)
        # assume any other value is a valid instance
        return redis_spec

    def get_proc(self, name, check_cache=False):
        if check_cache:
            # Note that if self.redis is None and check_cache is True, an
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
        try:
            proc_list = self.supervisor.getAllProcessInfo()
        except Exception:
            log.error("Failed to connect to %s", self)
            raise
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
        self.start_time = utcfromtimestamp(data['start']) \
            if data['start'] else None
        self.state = data['state']
        self.statename = data['statename']
        self.stderr_logfile = data['stderr_logfile']
        self.stdout_logfile = data['stdout_logfile']
        self.stop_time = utcfromtimestamp(data['stop']) \
            if data['stop'] else None

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

    @property
    def hostname(self):
        return self.host.name

    @property
    def settings(self):
        settings = self.host.rpc.vr.get_velociraptor_info(self.name)
        if not settings:
            return None
        return ProcData(settings)

    @staticmethod
    def parse_name(name):
        try:
            app_name, version, config_name, rel_hash, proc_name, port = \
                name.split('-')

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
        'mem_limit',
        'memsw_limit',
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

Credential = collections.namedtuple('Credential', 'username password')


class HashableDict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))


class SwarmFilter(six.text_type):
    """
    A regular expression indicating which swarm names to include.
    """
    exclusions = []
    "additional patterns to exclude"

    def matches(self, swarms):
        return filter(self.match, swarms)

    def match(self, swarm):
        return (
            not any(re.search(exclude, swarm.name, re.I)
                    for exclude in self.exclusions)
            and re.match(self, swarm.name)
        )


class QueryResult(Iterable):

    def __init__(self, vr, url, params):
        self.vr = vr
        self.sess = vr.session
        self.url = url
        self.params = params
        self._doc = None
        self._index = 0

    def __iter__(self):
        return self

    def load(self, next=None):
        url = self.url
        params = self.params or {}
        if next:
            next_url = urlparse(next)
            # See what query string args we have and update our
            # current params
            if next_url.query:
                params.update(dict(parse_qs(next_url.query)))

            # Be sure we have a trailing slash to avoid redirects
            if not next.endswith('/'):
                next += '/'

            url = self.vr._build_url(next_url.path)

        resp = self.sess.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def next(self):
        if not self._doc:
            self._doc = self.load()

        objects = self._doc['objects']
        meta = self._doc['meta']

        if self._index >= len(objects):
            # We reached the end of the objects in the list. Let's see
            # if there are more.
            if meta.get('next'):
                self._doc = self.load(meta['next'])
                self._index = 0
                return self.next()
            raise StopIteration()

        result = objects[self._index]
        self._index += 1
        return result


class Velociraptor(object):
    """
    A Velociraptor 2 HTTP API service
    """

    def __init__(self, base=None, username=None):
        self.base = base or self._get_base()
        self.username = username
        self.session.auth = self.get_credentials()

    @staticmethod
    def _get_base():
        """
        if 'deploy' resolves in this environment, use the hostname for which
        that name resolves.
        Override with 'VELOCIRAPTOR_URL'
        """
        try:
            name, aliaslist, addresslist = socket.gethostbyname_ex('deploy')
        except socket.gaierror:
            name = 'deploy'
        fallback = 'https://{name}/'.format(name=name)
        return os.environ.get('VELOCIRAPTOR_URL', fallback)

    def hostname(self):
        return six.moves.urllib.parse.urlparse(self.base).hostname

    session = requests.session()
    session.headers = {
        'Content-Type': 'application/json',
    }

    def get_credentials(self):
        username = self.username or getpass.getuser()
        hostname = self.hostname()

        _, _, default_domain = hostname.partition('.')
        auth_domain = os.environ.get(
            'VELOCIRAPTOR_AUTH_DOMAIN',
            default_domain
        )
        password = keyring.get_password(auth_domain, username)
        if password is None:
            prompt_tmpl = "{username}@{hostname}'s password: "
            prompt = prompt_tmpl.format(**vars())
            password = getpass.getpass(prompt)
        return Credential(username, password)

    def load(self, path):
        url = self._build_url(path)
        url += '?format=json&limit=9999'
        return self.session.get(url).json()

    def query(self, path, query):
        url = self._build_url(path)
        return QueryResult(self, url, params=query)

    def cut(self, build, **kwargs):
        """
        Cut a release
        """
        raise NotImplementedError("Can't cut releases (config?)")

    def _build_url(self, *parts):
        joiner = six.moves.urllib.parse.urljoin
        return functools.reduce(joiner, parts, self.base)

    def events(self):
        url = self._build_url('api/streams/events/')
        messages = sseclient.SSEClient(url, auth=self.session.auth)
        for msg in messages:
            yield json.loads(msg.data)


class BaseResource(object):

    def __init__(self, vr, obj=None):
        self._vr = vr
        self.__dict__.update(obj or {})

    def create(self):
        doc = copy.deepcopy(self.__dict__)
        doc.pop('_vr')
        url = self._vr._build_url(self.base)
        resp = self._vr.session.post(url, json.dumps(doc))
        if not resp.ok:
            print(resp.headers)
            try:
                doc = resp.json()
                if 'traceback' in doc:
                    print(doc['traceback'])
                else:
                    print(doc)
            except:
                print(resp.content)
            resp.raise_for_status()
        self.load(resp.headers['location'])
        return resp.headers['location']

    def load(self, url):
        url = self._vr._build_url(self.base, url)
        resp = self._vr.session.get(url)
        resp.raise_for_status()
        self.__dict__.update(resp.json())

    def save(self):
        url = self._vr._build_url(self.resource_uri)
        content = copy.deepcopy(self.__dict__)
        content.pop('_vr')
        resp = self._vr.session.put(url, json.dumps(content))
        resp.raise_for_status()
        return resp


class Swarm(BaseResource):
    """
    A VR Swarm
    """
    base = '/api/v1/swarms/'

    def __init__(self, vr, obj):
        self._vr = vr
        self.__dict__.update(obj)

    def __lt__(self, other):
        return self.name < other.name

    @property
    def name(self):
        return '-'.join([self.app_name, self.config_name, self.proc_name])

    def __repr__(self):
        return self.name

    @classmethod
    def by_name(cls, vr, swarm_name):
        app_name, config_name, proc_name = swarm_name.split('-')
        doc = list(vr.query(cls.base, {
            'app_name': app_name,
            'config_name': config_name,
            'proc_name': proc_name,
        }))[0]

        return cls(vr, doc)

    @classmethod
    def load_all(cls, vr):
        """
        Load all swarms
        """
        swarm_obs = vr.load(cls.base)['objects']
        swarms = [cls(vr, ob) for ob in swarm_obs]
        return swarms

    def dispatch(self, **changes):
        """
        Patch the swarm with changes and then trigger the swarm.
        """
        self.patch(**changes)
        trigger_url = self._vr._build_url(self.resource_uri, 'swarm/')
        resp = self._vr.session.post(trigger_url)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return None

    def patch(self, **changes):
        if not changes:
            return
        url = self._vr._build_url(self.resource_uri)
        resp = self._vr.session.patch(url, json.dumps(changes))
        resp.raise_for_status()
        self.__dict__.update(changes)

    @property
    def app(self):
        return self.app_name

    @property
    def recipe(self):
        return self.config_name

    def new_build(self):
        return Build._for_app_and_tag(
            self._vr,
            self.app,
            self.version,
        )


class Build(BaseResource):
    base = '/api/v1/builds/'

    @property
    def created(self):
        return 'id' in vars(self)

    def assemble(self):
        """
        Assemble a build
        """
        if not self.created:
            self.create()
        # trigger the build
        url = self._vr._build_url(self.resource_uri, 'build/')
        resp = self._vr.session.post(url)
        resp.raise_for_status()

    @classmethod
    def _for_app_and_tag(cls, vr, app, tag):
        obj = dict(app=App.base + app + '/', tag=tag)
        return cls(vr, obj)

    def __hash__(self):
        hd = HashableDict(self.__dict__)
        hd.pop('_vr')
        return hash(hd)

    def __eq__(self, other):
        return vars(self) == vars(other)


class App(BaseResource):
    base = '/api/v1/apps/'


class Buildpack(BaseResource):
    base = '/api/v1/buildpacks/'


class Squad(BaseResource):
    base = '/api/v1/squads/'


class OSImage(BaseResource):
    base = '/api/v1/squads/'


class Release(BaseResource):
    base = '/api/v1/releases/'

    def deploy(self, host, port, proc, config_name):
        url = self._vr._build_url(self.resource_uri, 'deploy/')
        data = dict(host=host, port=port, proc=proc, config_name=config_name)
        resp = self._vr.session.post(url, data=json.dumps(data))
        resp.raise_for_status()

    def parsed_config(self):
        return yaml.safe_load(self.config_yaml)


class Ingredient(BaseResource):
    base = '/api/v1/ingredients/'
