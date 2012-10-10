"""
Some wrappers around a Redis pubsub to make it work a little more nicely with
the Server Sent Events API in modern browsers.

To send a message:
import redis
from deployment.events import Sender

r = redis.Redis()
sender = Sender(r, channel='foo')
sender.publish('this is my message')


And to listen to messages:
import redis
from deployment.events import Listener
r = redis.Redis()
listener = Listener(r, channels=['foo'])
for message in listener:
    do_something(message)

In a Django view, you should actually just be able to do this:
def some_view(request):

"""

import json
import datetime
import uuid

import redis
from django.conf import settings

from deployment import utils


class Sender(object):
    def __init__(self, rcon_or_url, channel, buffer_key=None,
                 buffer_length=100):
        if isinstance(rcon_or_url, redis.StrictRedis):
            self.rcon = rcon_or_url
        elif isinstance(rcon_or_url, basestring):
            self.rcon = redis.StrictRedis(**utils.parse_redis_url(rcon_or_url))
        self.channel = channel
        self.buffer_key = buffer_key
        self.buffer_length = buffer_length

    def publish(self, message, name=None, tags=None, title=None):
        # Make an object with timestamp, ID, and payload
        data = {
            'time': datetime.datetime.utcnow().isoformat(),
            'message': message,
            'id': uuid.uuid1().hex,
            'tags': tags or [],
            'title': title or '',
        }
        if name:
            data['name'] = name

        payload = json.dumps(data)
        # Serialize it and stick it on the pubsub
        self.rcon.publish(self.channel, payload)

        # Also stick it on the end of our length-capped list, so consumers can
        # get a list of recent events as well as seeing current ones.
        if self.buffer_key:
            self.rcon.lpush(self.buffer_key, payload)
            self.rcon.ltrim(self.buffer_key, 0, self.buffer_length -
                                        1)


class Listener(object):
    def __init__(self, rcon_or_url, channels, buffer_key=None):
        if isinstance(rcon_or_url, redis.StrictRedis):
            self.rcon = rcon_or_url
        elif isinstance(rcon_or_url, basestring):
            self.rcon = redis.StrictRedis(**utils.parse_redis_url(rcon_or_url))
        self.channels = channels
        self.buffer_key = buffer_key
        self.pubsub = self.rcon.pubsub()
        self.pubsub.subscribe(channels)

    def __iter__(self):
        # If we've been initted with a buffer key, then get all the events off
        # that and spew them out before blocking on the pubsub.
        if self.buffer_key:
            buffered_events = self.rcon.lrange(self.buffer_key, 0, -1)
            for msg in reversed(list(buffered_events)):
                yield to_sse({'data': msg})

        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                yield to_sse(msg)


def to_sse(msg):
    """
    Given a Redis pubsub message that was published by a Sender (ie, has a JSON
    body with time, message, title, tags, and id), return a properly-formatted
    SSE string.
    """
    # Unfortunately, our SSE msg ID has to be carried inside the inner JSON,
    # since Redis doesn't natively give us such a field.
    data = json.loads(msg['data'])
    out = "id: " + data['id']
    if 'name' in data:
        out += '\nname: ' + data['name']

    payload = json.dumps({
        'time': data['time'],
        'message': data['message'],
        'tags': data['tags'],
        'title': data['title'],
    })
    out += '\ndata: ' + payload + '\n\n'
    return out


class ConnectionMiddleware(object):
    def process_request(self, request):
        # create a redis connection and tack it on to the request for views to
        # use later.
        redis_settings = utils.parse_redis_url(settings.EVENTS_PUBSUB_URL)
        self.redis = redis.StrictRedis(**redis_settings)
        request.event_sender = Sender(self.redis,
                                      settings.EVENTS_PUBSUB_CHANNEL,
                                      settings.EVENTS_BUFFER_KEY)

    def process_response(self, request, response):
        self.redis.connection_pool.disconnect()
        return response
