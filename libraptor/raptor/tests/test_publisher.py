import json

from mock import Mock, call

from raptor import publisher
from raptor.tests import FakeRPC
from raptor.models import Host, Proc

def get_tick():
    """
    Create and return a faked "tick" event as would be emitted from Supervisor.
    """
    epayload = 'when:1356028501'
    eheaders = {
        'ver': '3.0',
        'server': 'supervisor',
        'serial': '21',
        'pool': 'listener',
        'poolserial': '10',
        'eventname': 'TICK_60',
        'len': str(len(epayload)),
    }
    return publisher.Event(eheaders, epayload, 'somewhere')

# tick events just update cache
def test_ticks_get_fresh_data():
    server = Mock()
    host = Host('somewhere', server)
    tick = get_tick()
    try:
        publisher.handle_event(tick, host, 'fake_channel')
    except TypeError:
        # TypeError: 'Mock' object is not iterable
        # This happens after the bit we're testing, so ignore it.
        pass
    assert server.supervisor.mock_calls == [call.getAllProcessInfo()]


class MockContextManager(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.mock = Mock()
    def __enter__(self):
        return self.mock
    def __exit__(self, *_):
        pass

def test_events_cache_all_procs():
    server = FakeRPC()
    host = Host('somewhere', server)
    host.redis = Mock()
    host.redis.pipeline.return_value = pipe = MockContextManager()
    host.redis.hkeys.return_value = []
    tick = get_tick()
    publisher.handle_event(tick, host, 'fake_channel')
    calls = pipe.mock.mock_calls
    assert calls[0][0] == 'delete'
    cache_key, hashdict = calls[1][1]
    assert cache_key == 'host_procs:somewhere'
    for k in hashdict:
        assert k in ('dummyproc', 'node_example-v2-local-f96054b7-web-5003')
        # Make sure the saved values are json dicts
        procdata = json.loads(hashdict[k])
        assert isinstance(procdata, dict)
    assert calls[2] == call.expire('host_procs:somewhere', 600)
    assert calls[3] == call.execute()


def test_procstate_events_published():
    server = FakeRPC()
    host = Host('somewhere', server)
    host.redis = Mock()
    host.redis.pipeline.return_value = MockContextManager()
    host.redis.hkeys.return_value = []
    epayload = 'processname:dummyproc groupname:dummyproc from_state:STOPPED tries:0'
    eheaders = {
        'ver': '3.0',
        'server': 'supervisor',
        'serial': '21',
        'pool': 'listener',
        'poolserial': '10',
        'eventname': 'PROCESS_STATE_RUNNING',
        'len': str(len(epayload)),
    }
    ev = publisher.Event(eheaders, epayload, host.name)
    publisher.handle_event(ev, host, 'fake_channel')

    _, args, kwargs = host.redis.publish.mock_calls[0]
    assert args[0] == 'fake_channel'

    expected_data = Proc(host,
                         dict(host.supervisor.process_info['dummyproc'])).as_dict()
    expected_data['event'] = 'PROCESS_STATE_RUNNING'
    published_data = json.loads(args[1])
    assert expected_data == published_data


def test_removal_events_published():
    server = FakeRPC()
    host = Host('somewhere', server)
    host.redis = Mock()
    host.redis.pipeline.return_value = MockContextManager()
    host.redis.hkeys.return_value = []
    epayload = 'groupname:dummyproc'
    eheaders = {
        'ver': '3.0',
        'server': 'supervisor',
        'serial': '21',
        'pool': 'listener',
        'poolserial': '10',
        'eventname': 'PROCESS_GROUP_REMOVED',
        'len': str(len(epayload)),
    }
    ev = publisher.Event(eheaders, epayload, host.name)
    publisher.handle_event(ev, host, 'fake_channel')

    _, args, kwargs = host.redis.publish.mock_calls[0]
    assert args[0] == 'fake_channel'

    parsed = json.loads(args[1])
    assert parsed['name'] == 'dummyproc'
    assert parsed['event'] == 'PROCESS_GROUP_REMOVED'
    assert 'time' in parsed


def test_removals_include_id():
    server = FakeRPC()
    host = Host('somewhere', server)
    host.redis = Mock()
    host.redis.pipeline.return_value = MockContextManager()
    host.redis.hkeys.return_value = []
    epayload = 'groupname:dummyproc'
    eheaders = {
        'ver': '3.0',
        'server': 'supervisor',
        'serial': '21',
        'pool': 'listener',
        'poolserial': '10',
        'eventname': 'PROCESS_GROUP_REMOVED',
        'len': str(len(epayload)),
    }
    ev = publisher.Event(eheaders, epayload, host.name)
    publisher.handle_event(ev, host, 'fake_channel')

    _, args, kwargs = host.redis.publish.mock_calls[0]
    parsed = json.loads(args[1])
    assert parsed['id'] == 'somewhere-dummyproc'

def test_removals_include_parsed_procname():

    server = FakeRPC()
    host = Host('somewhere', server)
    host.redis = Mock()
    host.redis.pipeline.return_value = MockContextManager()
    host.redis.hkeys.return_value = []
    epayload = 'groupname:node_example-v2-local-f96054b7-web-5003'
    eheaders = {
        'ver': '3.0',
        'server': 'supervisor',
        'serial': '21',
        'pool': 'listener',
        'poolserial': '10',
        'eventname': 'PROCESS_GROUP_REMOVED',
        'len': str(len(epayload)),
    }
    ev = publisher.Event(eheaders, epayload, host.name)
    publisher.handle_event(ev, host, 'fake_channel')

    _, args, kwargs = host.redis.publish.mock_calls[0]
    parsed = json.loads(args[1])
    assert parsed['app_name'] == 'node_example'
    assert parsed['hash'] == 'f96054b7'
    assert parsed['proc_name'] == 'web'
    assert parsed['recipe_name'] == 'local'
    assert parsed['version'] == 'v2'
    assert parsed['port'] == 5003
