import redis

from vr.common.utils import parse_redis_url

def test_parse_redis_url():
    r = redis.StrictRedis(**parse_redis_url('redis://localhost:6379/0'))
    expected ={'db': 0,
               'decode_responses': False,
               'encoding': 'utf-8',
               'encoding_errors': 'strict',
               'host': 'localhost',
               'password': None,
               'port': 6379,
               'socket_timeout': None}

    for k, v in expected.items():
        assert k in r.connection_pool.connection_kwargs.keys()
        assert v == r.connection_pool.connection_kwargs[k]
