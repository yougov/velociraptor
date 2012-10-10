import datetime
import json
import urlparse
import logging

from django.http import HttpResponse
from celery.result import AsyncResult

from deployment import models


def json_response(obj, status=200):
    """Given a Python object, dump it to JSON and return a Django HttpResponse
    with the contents and proper Content-Type"""
    resp = HttpResponse(json.dumps(obj), status=status)
    resp['Content-Type'] = 'application/json'
    return resp


def get_task_status(task_id):
    """
    Given a task ID, return a dictionary with status information.
    """
    task = AsyncResult(task_id)
    status = {
        'successful': task.successful(),
        'result': str(task.result),  # result can be any picklable object
        'status': task.status,
        'ready': task.ready(),
        'failed': task.failed(),
    }

    if task.failed():
        status['traceback'] = task.traceback
    return status


def clean_task_value(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    elif isinstance(v, (basestring, int, float, tuple, list, dict, bool,
                        type(None))):
        return v


def task_to_dict(task):
    """
    Given a Celery TaskState instance, return a JSONable dict with its
    information.
    """
    # Make a copy of task.__dict__, leaving off any of the cached complex
    # objects
    return {k: clean_task_value(v) for k, v in task.__dict__.items() if not
           k.startswith('_')}


def parse_redis_url(url):
    """
    Given a url like redis://localhost:6379/0, return a dict with host, port,
    and db members.
    """
    parsed = urlparse.urlsplit(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port,
        'db': int(parsed.path.replace('/', '')),
    }


# Not a view!
def eventify(request, action, obj):
    """
    Helper function for simultaneously adding messages to the event log at
    /log/, as well as putting the same messages on the redis pubsub so they'll
    immediately pop up for all dashboard users.

    Depends on deployment.events.ConnectionMiddleware being enabled in order to
    get a redis connection per request.
    """
    user = request.user
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

    # put a message on the pubsub
    request.event_sender.publish(message, tags=['user', action], title=message)
