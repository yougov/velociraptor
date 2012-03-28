import json
import xmlrpclib

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django import forms
from django.core.urlresolvers import reverse
from celery.result import AsyncResult

from deployment.models import Host, Build
from deployment.forms import DeploymentForm


def dash(request):
    hosts = Host.objects.filter(active=True)
    return render(request, 'dash.html', locals())


SUPERVISOR_PORT = 9001


def json_response(obj):
    """Given a Python object, dump it to JSON and return a Django HttpResponse
    with the contents and proper Content-Type"""
    resp = HttpResponse(json.dumps(obj))
    resp['Content-Type'] = 'application/json'
    return resp


def api_host_status(request, host):
    """Display status of all supervisord-managed processes on a single host, in
    JSON"""
    server = xmlrpclib.Server('http://%s:%s' % (host, SUPERVISOR_PORT))
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
    server = xmlrpclib.Server('http://%s:%s' % (host, SUPERVISOR_PORT))
    state = server.supervisor.getProcessInfo(proc)
    # Add the host in too for convenvience's sake
    state['host'] = host
    return json_response(state)


def api_task_status(request, task_id):
    task = AsyncResult(task_id)
    status = {
        'successful': task.successful(),
        'result': str(task.result), # task.result can be any picklable python object. 
        'status': task.status,
        'ready': task.ready(),
        'failed': task.failed(),
        #'name': task.task_name, # this always seems to be empty
        'id': task.task_id
    }

    if task.failed():
        status['traceback'] = task.traceback

    return json_response(status)


class BuildUploadForm(forms.ModelForm):
    class Meta:
        model = Build


# XXX We shouldn't require CSRF on this view.  Would be nice to be able to
# upload from the command line.
def upload_build(request):
    form = BuildUploadForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        # process the form and redirect
        form.save()
        # set a message
        messages.success(request, '%s uploaded' % str(form.instance.file))
        # Redirect to the 'deploy' page.
        return HttpResponseRedirect(reverse('deploy'))
    return render(request, 'upload_build.html', vars())



def deploy(request):
    # will need a form that lets you create a new deployment.
    form = DeploymentForm(request.POST or None)

    if form.is_valid():
        # deploy the thing!
        # get the deployment function.
        # STUB
        import deployment
        func = deployment.tasks.deploy
        # /STUB
        # We made the form fields exactly match the arguments to the celery
        # task, so we can just use that dict for kwargs
        job = func.delay(**form.cleaned_data)
        # send it to a worker
        # save the new deployment
        # return a redirect.  Ideally to the page that lets you watch the
        # deployment as it happens.
        return redirect('api_task', task_id=job.task_id)

    return render(request, 'deploy.html', locals())
