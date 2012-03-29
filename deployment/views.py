import json
import xmlrpclib

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from celery.result import AsyncResult

from deployment.models import Host
from deployment.forms import (DeploymentForm, BuildUploadForm, BuildForm,
                              ReleaseForm)
from deployment import tasks


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


def build_hg(request):
    form = BuildForm(request.POST or None)
    if form.is_valid():
        job = tasks.build_hg.delay(**form.cleaned_data)
        return redirect('api_task', task_id=job.task_id)
    btn_text = "Build"
    return render(request, 'basic_form.html', vars())


def upload_build(request):
    form = BuildUploadForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        # process the form and redirect
        form.save()
        # set a message
        messages.success(request, '%s uploaded' % str(form.instance.file))
        # Redirect to the 'deploy' page.
        return HttpResponseRedirect(reverse('deploy'))
    enctype = "multipart/form-data"
    instructions = """Use this form to upload a build.  A valid build should have
    a Procfile, and have all app-specific dependencies already compiled into
    the env."""
    btn_text = 'Upload'
    return render(request, 'basic_form.html', vars())


def release(request):
    form = ReleaseForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(reverse('deploy'))
    enctype = "multipart/form-data"
    btn_text = 'Save'
    return render(request, 'basic_form.html', vars())


def deploy(request):
    # will need a form that lets you create a new deployment.
    form = DeploymentForm(request.POST or None)

    if form.is_valid():
        # We made the form fields exactly match the arguments to the celery
        # task, so we can just use that dict for kwargs
        job = tasks.deploy.delay(**form.cleaned_data)
        # send it to a worker
        # save the new deployment
        # return a redirect.  Ideally to the page that lets you watch the
        # deployment as it happens.
        return redirect('api_task', task_id=job.task_id)

    return render(request, 'deploy.html', locals())
