import xmlrpclib
import base64
from functools import wraps

from djcelery.models import TaskState
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django import http

from deployment import utils
from deployment import models
from deployment import tasks


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
    """Display status of all supervisord-managed processes on a single host, in
    JSON"""

    host = models.Host.objects.get(name=hostname)
    # TODO: use Cache-Control header to determine whether to pass use_cache
    # into procdata()
    data = host.procdata(use_cache=True)

    # add in the hostname
    data['host'] = host.name

    # add in things parsed from each procname
    data['procs'] = [models.make_proc(p['name'], host, p).as_dict() for p in
                     data['procs']]

    return utils.json_response(data)


@auth_required
def host_ports(request, hostname):
    host = models.Host.objects.get(name=hostname)
    return utils.json_response({
        'used_ports': list(host.get_used_ports()),
        'next_port': host.get_unused_port(),
    })


@auth_required
def host_proc(request, hostname, procname):
    """
    Display status of a single supervisord-managed process on a host, in
    JSON
    """
    host = models.Host.objects.get(name=hostname)
    proc = host.get_proc(procname)
    if request.method == 'DELETE':
        # check for and remove port lock if present
        try:
            pl = models.PortLock.objects.get(host=host, port=proc.port)
            pl.delete()
        except models.PortLock.DoesNotExist:
            pass
        # Do proc deletions syncronously instead of with Celery, since they're
        # fast and we want instant feedback.
        tasks.delete_proc(hostname, procname)

        # Make the cache forget about this proc
        host.procdata(use_cache=False)
        return utils.json_response({'name': procname, 'deleted': True})
    elif request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'start':
                host.start_proc(procname)
            elif action == 'stop':
                host.stop_proc(procname)
            elif action == 'restart':
                host.restart_proc(procname)
        except xmlrpclib.Fault as e:
            return utils.json_response({'fault': e.faultString}, 500)

    proc = host.get_proc(procname)
    return utils.json_response(proc.as_dict())


@auth_required
def task_recent(request):
    count = int(request.GET.get('count') or 20)
    # XXX HACK.  We're hiding tasks whose function names start with an
    # underscore, by using a kinda kludgy filter in the query.  Seems to keep
    # the task spam from repetitive things down, though.
    return utils.json_response({'tasks': [utils.task_to_dict(t) for t in
                                          TaskState.objects.exclude(name__contains='._')[:count]]})


@auth_required
def task_status(request, task_id):
    status = utils.get_task_status(task_id)
    status['id'] = task_id

    return utils.json_response(status)


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
