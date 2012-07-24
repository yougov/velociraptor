
import xmlrpclib
from djcelery.models import TaskState
from django.contrib.auth.decorators import login_required

from deployment import utils
from deployment import models
from deployment import tasks


# TODO: protect these json views with a decorator that returns a 403 instead of
# a redirect to the login page.  To be more ajax-friendly.
@login_required
def host(request):
    # list all hosts
    return utils.json_response({'hosts': [h.name for h in
                                    models.Host.objects.filter(active=True)]})


@login_required
def host_procs(request, hostname):
    """Display status of all supervisord-managed processes on a single host, in
    JSON"""

    host = models.Host.objects.get(name=hostname)
    # TODO: use Cache-Control header to determine whether to pass use_cache
    # into _get_procdata()
    procs = [utils.enhance_proc(host, p) for p in host._get_procdata(use_cache=True)]

    data = {
        'procs': procs,
        'host': hostname,
    }
    return utils.json_response(data)


@login_required
def host_ports(request, hostname):
    host = models.Host.objects.get(name=hostname)
    return utils.json_response({
        'used_ports': list(host.get_used_ports()),
        'next_port': host.get_unused_port(),
    })


@login_required
def host_proc(request, hostname, proc):
    """Display status of a single supervisord-managed process on a host, in
    JSON """
    host = models.Host.objects.get(name=hostname)
    if request.method == 'GET':
        state = host.rpc.getProcessInfo(proc)
    elif request.method == 'DELETE':
        # check for and remove port lock if present
        try:
            pr = models.make_proc(proc, host, None)
            pl = models.PortLock.objects.get(host=host, port=pr.port)
            pl.delete()
        except models.PortLock.DoesNotExist:
            pass
        # Do proc deletions syncronously instead of with Celery, since they're
        # fast and we want instant feedback.
        tasks.delete_proc(hostname, proc)

        # Make the cache forget about this proc
        host._get_procdata(use_cache=False)
        return utils.json_response({'name': proc, 'deleted': True})
    elif request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'start':
                host.rpc.startProcess(proc)
            elif action == 'stop':
                host.rpc.stopProcess(proc)
            elif action == 'restart':
                host.rpc.startProcess(proc)
                host.rpc.stopProcess(proc)
        except xmlrpclib.Fault as e:
            return utils.json_response({'fault': e.faultString}, 500)
        state = host.rpc.getProcessInfo(proc)
    # Add the host in too for convenience's sake
    out = utils.enhance_proc(host, state)
    return utils.json_response(out)


@login_required
def task_recent(request):
    count = int(request.GET.get('count') or 20)
    return utils.json_response({'tasks': [utils.task_to_dict(t)
                                    for t in TaskState.objects.all()[:count]]})


@login_required
def task_status(request, task_id):
    status = utils.get_task_status(task_id)
    status['id'] = task_id

    return utils.json_response(status)
