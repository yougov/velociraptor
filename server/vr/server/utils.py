import datetime
import json

import six

from django.http import HttpResponse
from celery.result import AsyncResult
import yaml


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
    date_types = datetime.datetime, datetime.date
    if isinstance(v, date_types):
        return v.isoformat()

    sp_types = int, float, tuple, list, dict, bool, type(None)
    sp_types += six.string_types
    if isinstance(v, sp_types):
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


def yamlize(dct):
    "Shortcut for convenience."
    return yaml.safe_dump(dct, default_flow_style=False)
