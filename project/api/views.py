import xmlrpclib
import base64
from functools import wraps

from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django import http
from django.conf import settings

from deployment import utils
from deployment import models
from deployment import tasks
from deployment import events


def auth_required(view_func):
    """
    An API-friendly alternative to Django's login_required decorator.  Honors
    both normal cookie-based auth as well as HTTP basic auth.  Returns status
    401 and a JSON response if auth not present.
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        # If the request is not authenticated, then check basic auth, and add
        # user object if it passes.  Else return a 401 Unauthorized with JSON
        # content

        nope = lambda: utils.json_response({'status': 401,
                                            'msg': 'Basic auth required'},
                                           status=401)
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        elif request.META.get('HTTP_AUTHORIZATION'):

            auth_type, data = request.META['HTTP_AUTHORIZATION'].split()
            if auth_type.lower() != 'basic':
                return nope()

            username, password = base64.b64decode(data).split(':', 1)
            user = authenticate(username=username, password=password)
            if not user:
                return nope()
            request.user = user
            return view_func(request, *args, **kwargs)
        else:
            return nope()
    return wrapped


@auth_required
def host(request):
    # list all hosts
    return utils.json_response({'hosts': [h.name for h in
                                    models.Host.objects.filter(active=True)]})


@auth_required
def host_procs(request, hostname):
    """
    Display status of all supervisord-managed processes on a single host, in
    JSON
    """
    host = models.Host.objects.get(name=hostname)
    procs = host.get_procs()
    dicts = [p.as_dict() for p in procs]
    # TODO: add in host_uri.  Or just call it 'host'
    # TODO: When log streaming is enabled, add in log_events_uri as well.
    return utils.json_response({
        'objects': dicts
    })


#@auth_required
def host_proc(request, hostname, procname):
    """
    Display status of a single supervisord-managed process on a host, in
    JSON
    """
    host = models.Host.objects.get(name=hostname)
    proc = host.get_proc(procname)
    if request.method == 'DELETE':
        events.eventify(request.user, 'destroy', proc.name)
        # check for and remove port lock if present
        try:
            pl = models.PortLock.objects.get(host=host, port=proc.port)
            pl.delete()
        except models.PortLock.DoesNotExist:
            pass

        tasks.delete_proc.delay(hostname, procname)
        return utils.json_response({'name': procname, 'deleted': True})
    elif request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'start':
                proc.start()
                events.eventify(request.user, 'start', proc.name)
            elif action == 'stop':
                proc.stop()
                events.eventify(request.user, 'stop', proc.name)
            elif action == 'restart':
                proc.restart()
                events.eventify(request.user, 'restart', proc.name)
        except xmlrpclib.Fault as e:
            return utils.json_response({'fault': e.faultString}, 500)

    proc = host.get_proc(procname)
    return utils.json_response(proc.as_dict())


@auth_required
def uptest_run(request, run_id):
    run = get_object_or_404(models.TestRun, id=run_id)
    return utils.json_response(run.results)


@auth_required
def uptest_latest(request):
    """
    Look up most recent test run and return its results.
    """
    runs = models.TestRun.objects.filter(end__isnull=False).order_by('-start')
    if len(runs):
        return utils.json_response(runs[0].results)
    else:
        raise http.Http404


@auth_required
def event_stream(request):
    """
    Stream worker events out to browser.
    """
    return http.HttpResponse(events.EventListener(
        settings.EVENTS_PUBSUB_URL,
        channels=[settings.EVENTS_PUBSUB_CHANNEL],
        buffer_key=settings.EVENTS_BUFFER_KEY,
        last_event_id=request.META.get('HTTP_LAST_EVENT_ID')
    ), mimetype='text/event-stream')


@auth_required
def proc_event_stream(request):
    return http.HttpResponse(events.ProcListener(
        settings.EVENTS_PUBSUB_URL,
        channel=settings.PROC_EVENTS_CHANNEL,
    ), mimetype='text/event-stream')
