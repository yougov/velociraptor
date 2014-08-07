import json
import datetime
import logging

import six
import redis
import sseclient
from django.conf import settings

from vr.common import utils
from vr.events import Sender


class EventSender(Sender):

    def publish(self, message, event=None, tags=None, title=None):
        # Make an object with timestamp, ID, and payload
        data = {
            'time': datetime.datetime.utcnow().isoformat(),
            'message': message,
            'tags': tags or [],
            'title': title or '',
        }

        payload = json.dumps(data)
        # Serialize it and stick it on the pubsub
        super(EventSender, self).publish(payload, event=event)

    def close(self):
        self.rcon.connection_pool.disconnect()


class ProcListener(object):
    def __init__(self, rcon_or_url, channel):
        if isinstance(rcon_or_url, redis.StrictRedis):
            self.rcon = rcon_or_url
        elif isinstance(rcon_or_url, six.string_types):
            self.rcon = redis.StrictRedis(**utils.parse_redis_url(rcon_or_url))
        self.channel = channel
        self.pubsub = self.rcon.pubsub()
        self.pubsub.subscribe([channel])

        self.rcon.publish(channel, 'flush')

    def __iter__(self):
        while 1:
            yield self.next()

    def next(self):
        while 1:
            msg = next(self.pubsub.listen())
            if msg['type'] == 'message':
                if msg['data'] == 'flush':
                    return ':\n'
                else:
                    ev = sseclient.Event(data=msg['data'], retry=1000)
                    return ev.dump()

    def close(self):
        self.rcon.connection_pool.disconnect()


def eventify(user, action, obj, detail=None):
    """
    Save a message to the user action log, application log, and events pubsub
    all at once.
    """
    fragment = '%s %s' % (action, obj)
    from vr.server import models  # Imported late to avoid circularity
    logentry = models.DeploymentLogEntry(
        type=action,
        user=user,
        message=fragment
    )
    logentry.save()
    # Also log it to actual python logging
    message = '%s: %s' % (user.username, fragment)
    logging.info(message)

    # put a message on the pubsub
    sender = EventSender(
        settings.EVENTS_PUBSUB_URL,
        settings.EVENTS_PUBSUB_CHANNEL,
        settings.EVENTS_BUFFER_KEY)
    sender.publish(detail or message, tags=['user', action], title=message)
    sender.close()
