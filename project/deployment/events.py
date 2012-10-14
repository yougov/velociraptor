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
import logging

import redis
from django.conf import settings
from django.http import HttpResponse

from deployment import utils, models


class Sender(object):
    def __init__(self,
                 rcon_or_url=settings.EVENTS_PUBSUB_URL,
                 channel=settings.EVENTS_PUBSUB_CHANNEL,
                 buffer_key=settings.EVENTS_BUFFER_KEY,
                 buffer_length=getattr(settings, 'EVENTS_BUFFER_LENGTH', 100)):
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
            'id': uuid.uuid1().hex,
            'time': datetime.datetime.utcnow().isoformat(),
            'message': message,
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
    def __init__(self,
                 rcon_or_url=settings.EVENTS_PUBSUB_URL,
                 channels=None,
                 buffer_key=settings.EVENTS_BUFFER_KEY,
                 last_event_id=None):
        if isinstance(rcon_or_url, redis.StrictRedis):
            self.rcon = rcon_or_url
        elif isinstance(rcon_or_url, basestring):
            self.rcon = redis.StrictRedis(**utils.parse_redis_url(rcon_or_url))
        if channels is None:
            channels = [settings.EVENTS_PUBSUB_CHANNEL]
        self.channels = channels
        self.buffer_key = buffer_key
        self.last_event_id = last_event_id
        self.pubsub = self.rcon.pubsub()
        self.pubsub.subscribe(channels)

        # Send a superfluous message down the pubsub to flush out stale
        # connections.
        for channel in self.channels:
            # Use buffer_key=None since these pings never need to be remembered
            # and replayed.
            sender = Sender(self.rcon, channel, None)
            sender.publish('_flush', tags=['hidden'])

    def __iter__(self):
        # stream out at least one dummy message so browsers don't complain
        # about getting nothing.
        #yield to_sse({'data': json.dumps({
            #'name': 'up',
            #'message': 'up',
            #'tags': ['up'],
            #'time': datetime.datetime.utcnow().isoformat(),
            #'title': 'up',
            #'id': uuid.uuid1().hex,
        #})})

        # If we've been initted with a buffer key, then get all the events off
        # that and spew them out before blocking on the pubsub.
        if self.buffer_key:
            buffered_events = self.rcon.lrange(self.buffer_key, 0, -1)

            # check whether msg with last_event_id is still in buffer.  If so,
            # trim buffered_events to have only newer messages.
            if self.last_event_id:
                # Note that we're looping through most recent messages first,
                # here
                counter = 0
                for msg in buffered_events:
                    if (json.loads(msg)['id'] == self.last_event_id):
                        break
                    counter += 1
                buffered_events = buffered_events[:counter]

            for msg in reversed(list(buffered_events)):
                # Stream out oldest messages first
                yield to_sse({'data': msg})

        for msg in self.pubsub.listen():
            if msg['type'] == 'message':
                yield to_sse(msg)

    def close(self):
        self.pubsub.close()
        self.rcon.connection_pool.disconnect()


class SSEResponse(HttpResponse):
    def __init__(self, rcon_or_url, channels, buffer_key=None,
                 last_event_id=None, *args, **kwargs):
        self.listener = Listener(rcon_or_url, channels, buffer_key,
                                 last_event_id)
        super(SSEResponse, self).__init__(self.listener,
                                          mimetype='text/event-stream',
                                          *args, **kwargs)

    def close(self):
        """
        This will be called by the WSGI server at the end of the request, even
        if the client disconnects midstream.  Unless you're using Django's
        runserver, in which case you should expect to see Redis connections
        build up until http://bugs.python.org/issue16220 is fixed.
        """
        self.listener.close()


def to_sse(msg):
    """
    Given a Redis pubsub message that was published by a Sender (ie, has a JSON
    body with time, message, title, tags, and id), return a properly-formatted
    SSE string.
    """
    data = json.loads(msg['data'])

    # According to the SSE spec, lines beginning with a colon should be
    # ignored.  We can use that as a way to force zombie listeners to try
    # pushing something down the socket and clean up their redis connections
    # when they get an error.
    # See http://dev.w3.org/html5/eventsource/#event-stream-interpretation
    if data['message'] == '_flush':
        return ":\n"  # Administering colonic!

    if 'id' in data:
        out = "id: " + data['id'] + '\n'
    else:
        out = ''
    if 'name' in data:
        out += 'name: ' + data['name'] + '\n'

    payload = json.dumps({
        'time': data['time'],
        'message': data['message'],
        'tags': data['tags'],
        'title': data['title'],
    })
    out += 'data: ' + payload + '\n\n'
    return out


# Not a view!
def eventify(user, action, obj):
    """
    Save a message to the user action log, application log, and events pubsub
    all at once.
    """
    fragment = '%s %s' % (action, obj)
    # create a log entry
    logentry = models.DeploymentLogEntry(
        type=action,
        user=user,
        message=fragment
    )
    logentry.save()
    # Also log it to actual python logging
    message = '%s: %s' % (user.username, fragment)
    logging.info(message)

    # put a message on the pubsub.  Just make a new redis connection when you
    # need to do this.  This is a lot lower traffic than doing a connection per
    # request.
    rcon = redis.StrictRedis(
        **utils.parse_redis_url(settings.EVENTS_PUBSUB_URL)
    )
    sender = Sender(rcon, settings.EVENTS_PUBSUB_CHANNEL,
                           settings.EVENTS_BUFFER_KEY)
    sender.publish(message, tags=['user', action], title=message)
    rcon.connection_pool.disconnect()
