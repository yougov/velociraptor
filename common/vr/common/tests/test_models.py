import datetime
import unittest
import json

import redis
import pytest

from vr.common.models import Host, ProcError, Build
from vr.common.utils import parse_redis_url, utc
from vr.common.tests import FakeRPC


def test_host_init_rpc():
    server = FakeRPC()
    host = Host('somewhere', server)
    assert host.supervisor is server.supervisor


def test_host_init_port():
    host = Host('somewhere', 9001)
    assert str(host.rpc) == '<ServerProxy for somewhere:9001/RPC2>'


def test_host_init_redis_url():
    server = FakeRPC()
    host = Host('somewhere', server, redis_or_url='redis://localhost:6379/0')
    assert isinstance(host.redis, redis.StrictRedis)


def test_get_procs_len():
    server = FakeRPC()
    host = Host('somewhere', server)
    procs = host.get_procs()
    assert len(procs) == 2

class FakeProcCase(unittest.TestCase):
    def setUp(self):
        self.server = FakeRPC()
        self.host = Host('somewhere', self.server)
        self.dummyproc = self.host.get_proc('dummyproc')
        self.nodeproc = self.host.get_proc('node_example-v2-local-f96054b7-web-5003')

    def test_hostname(self):
        assert self.dummyproc.host.name == 'somewhere'

    def test_name(self):
        assert self.dummyproc.name == 'dummyproc'

    def test_start(self):
        ts = datetime.datetime(2012, 12, 19, 6, 19, 46, tzinfo=utc)
        assert self.dummyproc.start_time == ts

    def test_stop(self):
        ts = datetime.datetime(2012, 12, 19, 6, 19, 46, tzinfo=utc)
        assert self.dummyproc.stop_time == ts

    def test_now(self):
        ts = datetime.datetime(2012, 12, 19, 6, 19, 46, tzinfo=utc)
        assert self.dummyproc.now == ts

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
            'app_name': 'dummyproc',
            'description': 'pid 5556, uptime 16:05:53',
            'exitstatus': 0,
            'group': 'dummyproc',
            'hash': 'UNKNOWN',
            'host': 'somewhere',
            'id': 'somewhere-dummyproc',
            'jsname': 'dummyproc',
            'logfile': '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
            'name': 'dummyproc',
            'now': '2012-12-19T06:19:46+00:00',
            'pid': 5556,
            'port': 0,
            'proc_name': 'dummyproc',
            'config_name': 'UNKNOWN',
            'spawnerr': '',
            'start_time': '2012-12-19T06:19:46+00:00',
            'state': 20,
            'statename': 'RUNNING',
            'stderr_logfile': '/tmp/pub.log',
            'stdout_logfile': '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
            'stop_time': '2012-12-19T06:19:46+00:00',
            'version': 'UNKNOWN',
        }

    def test_app_name(self):
        assert self.nodeproc.app_name == 'node_example'

    def test_version(self):
        assert self.nodeproc.version == 'v2'

    def test_config_name(self):
        assert self.nodeproc.config_name == 'local'

    def test_hash(self):
        assert self.nodeproc.hash == 'f96054b7'

    def test_proc_name(self):
        assert self.nodeproc.proc_name == 'web'

    def test_port(self):
        assert self.nodeproc.port == 5003

    def test_as_node(self):
        assert self.nodeproc.as_node() == 'somewhere:5003'

    def test_shortname(self):
        assert self.nodeproc.shortname() == 'node_example-v2-web'


def test_datetime_none():
    server = FakeRPC()
    server.supervisor.process_info['dummyproc']['now'] = 0
    host = Host('somewhere', server)
    proc = host.get_proc('dummyproc')
    assert proc.now is None


class RedisCacheTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeRPC()
        self.supervisor = self.server.supervisor
        self.redis = redis.StrictRedis(**parse_redis_url('redis://localhost:6379/15'))
        self.host = Host('somewhere', self.server,
                         redis_or_url=self.redis)

    def tearDown(self):
        # self.redis.delete(self.host.cache_key)
        pass

    def test_proc_get_cache_set(self):
        # Ensure that single-proc data fetched from host is saved to cache
        self.host.get_proc('dummyproc', check_cache=True)
        cached = self.redis.hget(self.host.cache_key, 'dummyproc')
        assert json.loads(cached) == self.supervisor.process_info['dummyproc']

    def test_procs_get_cache_set(self):
        # Ensure that full data fetched from host is saved to cache
        self.host.get_procs(check_cache=True)
        cached = self.redis.hgetall(self.host.cache_key)
        parsed = {k: json.loads(v) for k, v in cached.items()}
        assert parsed == self.supervisor.process_info

    def test_get_procs_uses_cache(self):
        self.host.get_procs(check_cache=True)
        # If we actually hit the RPC, an exception will be raised
        self.supervisor.exception = AssertionError('cache not used')
        self.host.get_procs(check_cache=True)

    def test_get_proc_uses_cache(self):
        self.host.get_proc('dummyproc', check_cache=True)
        # If we actually hit the RPC, an exception will be raised
        self.supervisor.exception = AssertionError('cache not used')
        self.host.get_proc('dummyproc', check_cache=True)

    def test_full_set_partial_get(self):
        # Ensure that data cached from a full get is used when just requesting
        # a single proc
        self.host.get_procs(check_cache=True)
        # If we actually hit the RPC, an exception will be raised
        self.supervisor.exception = AssertionError('cache not used')
        self.host.get_proc('dummyproc', check_cache=True)

    def test_absent_proc_decached(self):
        # Test that if a proc is in the cache but not returned from the host
        # when get_procs is called, it gets removed from the cache
        data = dict(self.supervisor.process_info['dummyproc'])
        data['group'] = data['name'] = 'deadproc'
        self.redis.hset(self.host.cache_key, 'deadproc', json.dumps(data))

        # Requesting just this proc should return data
        assert self.host.get_proc('deadproc', check_cache=True).name == 'deadproc'

        # But requesting all procs, with deadproc absent from the Supervisor
        # data, should clear him from cache
        all_procs = [p.name for p in self.host.get_procs(check_cache=False)]
        assert 'deadproc' not in all_procs

    def test_nonexistent_proc_raises_proc_error(self):
        with pytest.raises(ProcError):
            self.host.get_proc('nonexistent')

def test_build_sets():
    """
    A set of builds should resolve distinct builds
    """
    b1 = Build(None, {'app': 'foo'})
    b2 = Build(None, {'app': 'foo'})
    b3 = Build(None, {'app': 'bar'})
    assert set([b1, b2, b3]) == set([b1, b3])
