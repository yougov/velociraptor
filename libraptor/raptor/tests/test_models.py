import xmlrpclib
import datetime
import unittest
import json

import redis
import pytest

from raptor.models import Host, Proc
from raptor.utils import parse_redis_url


# A fake Supervisor xmlrpc interface.
class FakeSupervisor(object):
    # Set this at test time in order to fake an exception.
    exception = None

    # Set this dict in order to control what data comes back from the
    # getAllProcessInfo and getProcessInfo calls.  (Slightly tweaked to include
    # a 'host' key.)
    process_info = {
        'dummyproc': {
            'description': 'pid 5556, uptime 16:05:53',
            'exitstatus': 0,
            'group':  'dummyproc',
            'logfile':  '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
            'name':  'dummyproc',
            'now': 1355897986,
            'pid': 5556,
            'spawnerr':  '',
            'start': 1355897986,
            'state': 20,
            'statename':  'RUNNING',
            'stderr_logfile':  '/tmp/pub.log',
            'stdout_logfile':  '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
            'stop': 1355897986,
            'host': 'somewhere'},
        'node_example-v2-local-f96054b7-web-5003': {
            'description': 'Exited too quickly (process log may have details)',
            'exitstatus': 0,
            'group': 'node_example-v2-local-f96054b7-web-5003',
            'logfile': '/apps/procs/node_example-v2-local-f96054b7-web-5003/log',
            'name': 'node_example-v2-local-f96054b7-web-5003',
            'now': 1355955939,
            'pid': 0,
            'spawnerr': 'Exited too quickly (process log may have details)',
            'start': 1355898065,
            'state': 200,
            'statename': 'FATAL',
            'stderr_logfile': '/var/log/supervisor/node_example-v2-local-f96054b7-web-5003-stderr---supervisor-gL_lvl.log',
            'stdout_logfile': '/apps/procs/node_example-v2-local-f96054b7-web-5003/log',
            'stop': 1355898065}}

    def _fake_fault(self):
        if self.exception:
            raise self.exception

    def getProcessInfo(self, name):
        self._fake_fault()
        return self.process_info[name]

    def getAllProcessInfo(self):
        self._fake_fault()
        return self.process_info.values()

class FakeServer(object):
    def __init__(self):
        self.supervisor = FakeSupervisor()


def test_host_init_rpc():
    server = FakeServer()
    host = Host('somewhere', server)
    assert host.supervisor is server.supervisor


def test_host_init_port():
    host = Host('somewhere', 9001)
    assert str(host.rpc) == '<ServerProxy for somewhere:9001/RPC2>'


def test_host_init_redis_url():
    server = FakeServer()
    host = Host('somewhere', server, redis_or_url='redis://localhost:6379/0')
    assert isinstance(host.redis, redis.StrictRedis)


def test_get_procs():
    server = FakeServer()
    host = Host('somewhere', server)
    procs = host.get_procs()
    assert len(procs) == 2

class FakeProcCase(unittest.TestCase):
    def setUp(self):
        self.server = FakeServer()
        self.host = Host('somewhere', self.server)
        self.dummyproc = self.host.get_proc('dummyproc')
        self.nodeproc = self.host.get_proc('node_example-v2-local-f96054b7-web-5003')

    def test_hostname(self):
        assert self.dummyproc.host.name == 'somewhere'

    def test_name(self):
        assert self.dummyproc.name == 'dummyproc'

    def test_start(self):
        assert self.dummyproc.start == datetime.datetime(2012, 12, 18, 22, 19, 46)

    def test_stop(self):
        assert self.dummyproc.stop == datetime.datetime(2012, 12, 18, 22, 19, 46)

    def test_now(self):
        assert self.dummyproc.now == datetime.datetime(2012, 12, 18, 22, 19, 46)

    def test_description(self):
        assert self.dummyproc.description == 'pid 5556, uptime 16:05:53'

    def test_group(self):
        assert self.dummyproc.group == 'dummyproc'

    def test_logfile(self):
        assert self.dummyproc.logfile == '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log'

    def test_pid(self):
        assert self.dummyproc.pid == 5556

    def test_spawnerr(self):
        assert self.dummyproc.spawnerr == ''

    def test_statename(self):
        assert self.dummyproc.statename == 'RUNNING'

    def test_stderr_logfile(self):
        assert self.dummyproc.stderr_logfile == '/tmp/pub.log'

    def test_stdout_logfile(self):
        assert self.dummyproc.stdout_logfile == '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log'

    def test_as_dict(self):
        assert self.dummyproc.as_dict() == {
             'app_name': '~UNKNOWN',
             'description': 'pid 5556, uptime 16:05:53',
             'exitstatus': 0,
             'group': 'dummyproc',
             'hash': 'UNKNOWN',
             'host': 'somewhere',
             'id': 'somewhere-dummyproc',
             'jsname': 'dummyproc',
             'logfile': '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
             'name': 'dummyproc',
             'now': '2012-12-18T22:19:46',
             'pid': 5556,
             'port': 0,
             'proc_name': 'dummyproc',
             'recipe_name': 'UNKNOWN',
             'spawnerr': '',
             'start': '2012-12-18T22:19:46',
             'state': 20,
             'statename': 'RUNNING',
             'stderr_logfile': '/tmp/pub.log',
             'stdout_logfile': '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
             'stop': '2012-12-18T22:19:46',
             'version': 'UNKNOWN'}

    def test_app_name(self):
        assert self.nodeproc.app_name == 'node_example'

    def test_version(self):
        assert self.nodeproc.version == 'v2'

    def test_recipe_name(self):
        assert self.nodeproc.recipe_name == 'local'

    def test_hash(self):
        assert self.nodeproc.hash == 'f96054b7'

    def test_proc_name(self):
        assert self.nodeproc.proc_name == 'web'

    def test_port(self):
        assert self.nodeproc.port == 5003

    def test_as_node(self):
        assert self.nodeproc.as_node() == 'somewhere:5003'

    def test_shortname(self):
        assert self.nodeproc.shortname() == 'node_example-web'


def test_datetime_none():
    server = FakeServer()
    server.supervisor.process_info['dummyproc']['now'] = 0
    host = Host('somewhere', server)
    proc = host.get_proc('dummyproc')
    assert proc.now is None


class RedisCacheTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeServer()
        self.supervisor = self.server.supervisor
        self.redis = redis.StrictRedis(**parse_redis_url('redis://localhost:6379/0'))
        self.host = Host('somewhere', self.server,
                         redis_or_url=self.redis)

    def tearDown(self):
        # clear out all cache entries
        for k in self.redis.hkeys(self.host.cache_key):
            self.redis.hdel(self.host.cache_key, k)

    def test_proc_get_cache_set(self):
        # Ensure that single-proc data fetched from host is saved to cache
        self.host.get_proc('dummyproc', use_cache=True)
        cached = self.redis.hget(self.host.cache_key, 'dummyproc')
        assert json.loads(cached) == self.supervisor.process_info['dummyproc']

    def test_procs_get_cache_set(self):
        # Ensure that full data fetched from host is saved to cache
        self.host.get_procs(use_cache=True)
        cached = self.redis.hgetall(self.host.cache_key)
        parsed = {k: json.loads(v) for k, v in cached.items()}
        parsed.pop('__full__')
        assert parsed == self.supervisor.process_info

    def test_get_procs_uses_cache(self):
        self.host.get_procs(use_cache=True)
        # If we actually hit the RPC, an exception will be raised
        self.supervisor.exception = AssertionError('cache not used')
        self.host.get_procs(use_cache=True)

    def test_get_proc_uses_cache(self):
        self.host.get_proc('dummyproc', use_cache=True)
        # If we actually hit the RPC, an exception will be raised
        self.supervisor.exception = AssertionError('cache not used')
        self.host.get_proc('dummyproc', use_cache=True)

    def test_full_set_partial_get(self):
        # Ensure that data cached from a full get is used when just requesting
        # a single proc
        self.host.get_procs(use_cache=True)
        # If we actually hit the RPC, an exception will be raised
        self.supervisor.exception = AssertionError('cache not used')
        self.host.get_proc('dummyproc', use_cache=True)

    def test_partial_set_full_get(self):
        # Ensure that the cache is only used to return full proc data if it's
        # been populated by a full (not just partial) fetch.
        self.host.get_proc('dummyproc', use_cache=True)
        self.supervisor.exception = AssertionError('Supervisor called')
        with pytest.raises(AssertionError):
            self.host.get_procs(use_cache=True)






# Test that things get stored in the cache when a fetch is done with
# use_cache=True.

# Test that things are fetched from the cache when a fetch is done with
# use_cache=True.

# Test that if a host is in the cache but not returned from the host, it gets
# removed from the cache.
