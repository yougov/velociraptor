import xmlrpclib
import base64
from functools import wraps
import json

from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django import http
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import sseclient
import requests

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
    procs = host.get_procs(check_cache=True)
    dicts = [p.as_dict() for p in procs]
    return utils.json_response({
        'objects': dicts
    })


@auth_required
def swarm_procs(request, swarm_id):
    """
    Display status of all processes for a given swarm
    """
    swarm = models.Swarm.objects.get(id=swarm_id)
    return utils.json_response({
        'objects': [p.as_dict() for p in swarm.get_procs(check_cache=True)]
    })

@auth_required
@csrf_exempt
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

        # The web proc will perform deletions itself instead of sending them to
        # a worker, because otherwise we could be asking a worker to delete
        # itself.
        tasks.delete_proc(hostname, procname)
        return utils.json_response({'name': procname, 'deleted': True})
    elif request.method == 'POST':
        parsed = json.loads(request.body)
        # TODO: allow separate title/details from event.eventify
        try:
            if parsed['action'] == 'start':
                events.eventify(request.user, 'start', proc.shortname())
                proc.start()
            elif parsed['action'] == 'stop':
                events.eventify(request.user, 'stop', proc.shortname())
                proc.stop()
            elif parsed['action'] == 'restart':
                events.eventify(request.user, 'restart', proc.shortname())
                proc.restart()
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



class ProcTailer(object):
    """
    Given a hostname, port, and procname, connect to the log tailing endpoint
    for that proc and yield a string for each line in the log, as they come.
    """
    def __init__(self, hostname, port, procname):
        self.hostname = hostname
        self.port = port
        self.procname = procname
        self.buf = u''

        self._connect()

    def _connect(self):
        url = 'http://%s:%s/logtail/%s' % (self.hostname, self.port, self.procname)

        self.resp = requests.get(url, stream=True)
        self.resp.raise_for_status()

    def __iter__(self):
        while True:
            yield self.next()

    def next(self):
        while '\n' not in self.buf:
            self.buf += next(self.resp.iter_content(decode_unicode=True))
        head, sep, tail = self.buf.partition('\n')
        self.buf = tail
        return head + '\n'

    def close(self):
        # Close the connection
        self.resp.raw._fp.close()
        # Release the connection from the pool
        self.resp.raw.release_conn()


class SSETailer(ProcTailer):
    """
    Given a hostname, port, and procname, yield one event per log line.
    """

    def next(self):
        # Remove the trailing newline from the data
        data = super(SSETailer, self).next()[:-1]
        e = sseclient.Event(data=data)
        return e.dump()

@auth_required
def proc_log_stream(request, hostname, procname):
    if request.META['HTTP_ACCEPT'] == 'text/event-stream':
        return http.HttpResponse(SSETailer(hostname, settings.SUPERVISOR_PORT,
                                           procname),
                                 content_type='text/event-stream')
    return http.HttpResponse(ProcTailer(hostname, settings.SUPERVISOR_PORT,
                                        procname), content_type='text/plain')
