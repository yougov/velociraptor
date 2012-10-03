"""
Some wrappers around a Redis pubsub to make it work a little more nicely with
the Server Sent Events API in modern browsers.

To send a message:
import redis
from deployment.pubsub import Sender

r = redis.Redis()
sender = Sender(r, channel='foo')
sender.publish('this is my message')


And to listen to messages:
import redis
from deployment.pubsub import Listener
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


class Sender(object):
    def __init__(self, redis_connection, channel):
        self.redis_connection = redis_connection
        self.channel = channel

    def publish(self, message, name=None):
        # Make an object with timestamp, ID, and payload
        data = {
            'time': datetime.datetime.utcnow().isoformat(),
            'message': message,
            'id': uuid.uuid1().hex
        }
        if name:
            data['name'] = name
        # Serialize it and stick it on the pubsub
        self.redis_connection.publish(self.channel, json.dumps(data))


def to_sse(msg):
    """
    Given a Redis pubsub message that was published by a Sender (ie, has a JSON
    body with time, message, and id), return a properly-formatted SSE string.
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
    })
    out += '\ndata: ' + payload + '\n\n'
    return out


class Listener(object):
    def __init__(self, redis_connection, channels):
        self.redis_connection = redis_connection
        self.channels = channels
        self.pubsub = self.redis_connection.pubsub()
        self.pubsub.subscribe(channels)

    def __iter__(self):
        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                yield to_sse(msg)
