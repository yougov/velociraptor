import json
import ast
import xmlrpclib

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from celery.result import AsyncResult
from celery.task.control import inspect

from deployment.models import Host, App, Release, Build, Profile, remember
from deployment.forms import (DeploymentForm, BuildUploadForm, BuildForm,
                              ReleaseForm)
from deployment import tasks


def dash(request):
    hosts = Host.objects.filter(active=True)
    apps = App.objects.all()
    return render(request, 'dash.html', vars())


def json_response(obj):
    """Given a Python object, dump it to JSON and return a Django HttpResponse
    with the contents and proper Content-Type"""
    resp = HttpResponse(json.dumps(obj))
    resp['Content-Type'] = 'application/json'
    return resp

def api_host(request):
    # list all hosts
    return json_response({'hosts': [h.name for h in
                                    Host.objects.filter(active=True)]})


def api_host_status(request, hostname):
    """Display status of all supervisord-managed processes on a single host, in
    JSON"""
    server = xmlrpclib.Server('http://%s:%s' % (hostname, settings.SUPERVISOR_PORT))
    states = server.supervisor.getAllProcessInfo()
    # It's a security vulnerability to return a top-level JSON array, so wrap
    # it in an object and stick some extra info on.
    data = {
        'states': states,
        'host': hostname,
    }
    return json_response(data)


def api_host_ports(request, hostname):
    host = Host.objects.get(name=hostname)
    return json_response({
        'used_ports': list(host.get_used_ports()),
        'next_port': host.get_unused_port(),
    })


def api_proc_status(request, host, proc):
    """Display status of a single supervisord-managed process on a host, in JSON"""
    server = xmlrpclib.Server('http://%s:%s' % (host, settings.SUPERVISOR_PORT))
    state = server.supervisor.getProcessInfo(proc)
    # Add the host in too for convenvience's sake
    state['host'] = host
    return json_response(state)


def api_task_active(request):
    # Make a list of jobs, each one a dict with a desc and an id.
    out = []
    for hostname, tasklist in inspect().active().items():
        # data will be formatted like
        # http://ask.github.com/celery/userguide/workers.html#dump-of-currently-executing-tasks

        # XXX This is kinda ugly.  Think of a better way to get this data out
        # in a nice format for the JS to display
        for task in tasklist:
            kwargs = ast.literal_eval(task['kwargs'])
            if task['name'] == "deployment.tasks.build_hg":
                app = App.objects.get(id=int(kwargs['app_id']))
                desc = 'hg build of ' + app.name
                out.append({'id': task['id'], 'desc': desc})
            elif task['name'] == 'deployment.tasks.deploy':
                release = Release.objects.get(id=int(kwargs['release_id']))
                kwargs['appname'] = release.build.app.name
                desc = '%(appname)s deploy to %(host)s:%(port)s' % kwargs
                out.append({'id': task['id'], 'desc': desc})

    # XXX DEBUG
    #out.append({'id': 'blerg', 'desc': 'fake task'})

    return json_response({'tasks': out})


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
        app = App.objects.get(id=form.cleaned_data['app_id'])
        remember('build', 'built %s-%s' % (app.name, form.cleaned_data['tag']))
        return redirect('dash')
    btn_text = "Build"
    return render(request, 'basic_form.html', vars())


def upload_build(request):
    form = BuildUploadForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        # process the form and redirect
        form.save()
        # set a message
        remember('build', 'uploaded build %s' % str(form.instance.file))
        # Redirect to the 'deploy' page.
        return HttpResponseRedirect(reverse('deploy'))
    enctype = "multipart/form-data"
    instructions = """Use this form to upload a build.  A valid build should have
    a Procfile, and have all app-specific dependencies already compiled into
    the env."""
    btn_text = 'Upload'
    return render(request, 'basic_form.html', vars())


def release(request):
    form = ReleaseForm(request.POST or None)
    if form.is_valid():
        build=Build.objects.get(id=form.cleaned_data['build_id'])
        r = Release(
            build=build,
            config=Profile.objects.get(id=form.cleaned_data['profile_id']).assemble(),
        )
        r.save()
        remember('release', 'created release %s with %s' % (r.id, str(build)))
        return HttpResponseRedirect(reverse('deploy'))
    btn_text = 'Save'
    return render(request, 'basic_form.html', vars())


def deploy(request):
    # will need a form that lets you create a new deployment.
    form = DeploymentForm(request.POST or None)

    if form.is_valid():
        # We made the form fields exactly match the arguments to the celery
        # task, so we can just use that dict for kwargs
        job = tasks.deploy.delay(**form.cleaned_data)
        form.cleaned_data['release'] = str(Release.objects.get(id=form.cleaned_data['release_id']))
        msg = ('deployed %(release)s:%(proc)s to %(host)s:%(port)s'
               % form.cleaned_data)
        remember('deployment', msg)
        return redirect('dash')

    return render(request, 'deploy.html', locals())
