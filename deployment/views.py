from collections import OrderedDict
import json
import xmlrpclib

from django.shortcuts import render
from django.http import HttpResponse
from celery.tasks import AsyncResult

from deployment.models import Host
from deployment.forms import DeploymentForm


def dash(request):
    hosts = Host.objects.filter(active=True)
    return render(request, 'dash.html', locals())


SUPERVISOR_PORT = 9001

def connect_supd(host):
    url = 'http://%s:%s' % (host, SUPERVISOR_PORT)
    return xmlrpclib.Server(url)


def json_response(obj):
    """Given a Python object, dump it to JSON and return a Django HttpResponse
    with the contents and proper Content-Type"""
    resp = HttpResponse(json.dumps(obj))
    resp['Content-Type'] = 'application/json'
    return resp


def api_host_status(request, host):
    """Display status of all supervisord-managed processes on a single host, in
    JSON"""
    server = connect_supd(host)
    states = server.supervisor.getAllProcessInfo()
    # It's a security vulnerability to return a top-level JSON array, so wrap
    # it in an object and stick some extra info on.
    data = {
        'states': states,
        'host': host,
    }
    return json_response(data)


def api_proc_status(request, host, proc):
    """Display status of a single supervisord-managed process on a host, in JSON"""
    server = connect_supd(host)
    state = server.supervisor.getProcessInfo(proc)
    # Add the host in too for convenvience's sake
    state['host'] = host
    return json_response(state)


def api_task_status(request, task_id):
    task = AsyncResult(task_id)
    status = {
        'successful': task.successful(),
        'result': task.result,
        'status': task.status,
        'ready': task.ready(),
        'failed': task.failed(),
        'name': task.task_name,
        'id': task.task_id
    }
    if task.failed:
        status['traceback'] = task.traceback
    return json_response(status)

def deploy(request):
    # will need a form that lets you create a new deployment.
    form = DeploymentForm(request.POST or None)

    if form.is_valid():
        # deploy the thing!
        # get the deployment function.
        # STUB
        import deployment
        func = deployment.tasks.get_host_os_version
        # /STUB
        job = func.delay(
            form.cleaned_data['host'],
            form.cleaned_data['user'],
            form.cleaned_data['password'],
        )
        # send it to a worker
        # save the new deployment
        # return a redirect.  Ideally to the page that lets you watch the
        # deployment as it happens.
    return render(request, 'deploy.html', locals())
