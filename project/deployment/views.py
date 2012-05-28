import json
import ast
import xmlrpclib
import base64
import copy
import collections
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from celery.result import AsyncResult
from celery.task.control import inspect

from deployment.models import (Host, App, Release, Build, Profile, Squad,
                               Swarm, remember)
from deployment import forms
from deployment import tasks


@login_required
def dash(request):
    hosts = Host.objects.filter(active=True)
    apps = App.objects.all()
    supervisord_web_port = settings.SUPERVISORD_WEB_PORT
    return render(request, 'dash.html', vars())


def json_response(obj, status=200):
    """Given a Python object, dump it to JSON and return a Django HttpResponse
    with the contents and proper Content-Type"""
    resp = HttpResponse(json.dumps(obj), status=status)
    resp['Content-Type'] = 'application/json'
    return resp

# TODO: protect these json views with a decorator that returns a 403 instead of
# a redirect to the login page.  To be more ajax-friendly.
@login_required
def api_host(request):
    # list all hosts
    return json_response({'hosts': [h.name for h in
                                    Host.objects.filter(active=True)]})


@login_required
def api_host_status(request, hostname):
    """Display status of all supervisord-managed processes on a single host, in
    JSON"""
    server = xmlrpclib.Server('http://%s:%s' % (hostname, settings.SUPERVISOR_PORT))
    states = server.supervisor.getAllProcessInfo()

    data = {
        'states': states,
        'host': hostname,
    }
    return json_response(data)


@login_required
def api_host_ports(request, hostname):
    host = Host.objects.get(name=hostname)
    return json_response({
        'used_ports': list(host.get_used_ports()),
        'next_port': host.get_unused_port(),
    })


def get_creds(request):
    """
    Given a request made by a logged-in user, pull off the username/password
    that we saved in the session so they can be used to do some action on the
    user's behalf.  Return a tuple of username, password.
    """
    username, password = base64.b64decode(
        request.session['creds']).split(':')
    Credential = collections.namedtuple('Credential', 'username password')
    return Credential(username, password)


@login_required
def api_host_proc(request, host, proc):
    """Display status of a single supervisord-managed process on a host, in JSON"""
    server = xmlrpclib.Server('http://%s:%s' % (host, settings.SUPERVISOR_PORT))
    if request.method == 'GET':
        state = server.supervisor.getProcessInfo(proc)
    elif request.method == 'DELETE':
        # Do proc deletions syncronously instead of with Celery, since they're
        # fast and we want instant feedback.
        user, password = get_creds(request)
        tasks.delete_proc(host, proc, user, password)
        state = {'name': proc, 'deleted': True}
        # TODO: check for and remove port lock if present
    elif request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'start':
                server.supervisor.startProcess(proc)
            elif action == 'stop':
                server.supervisor.stopProcess(proc)
            elif action == 'restart':
                server.supervisor.startProcess(proc)
                server.supervisor.stopProcess(proc)
        except xmlrpclib.Fault as e:
            return json_response({'fault': e.faultString}, 500)
        state = server.supervisor.getProcessInfo(proc)
    # Add the host in too for convenience's sake
    state['host'] = host
    return json_response(state)


@login_required
def api_task_active(request):
    # Make a list of jobs, each one a dict with a desc and an id.
    out = []
    active = inspect().active()
    if active:
        for hostname, tasklist in active.items():
            # data will be formatted like
            # http://ask.github.com/celery/userguide/workers.html#dump-of-currently-executing-tasks

            # XXX This is kinda ugly.  Think of a better way to get this data out
            # in a nice format for the JS to display
            for task in tasklist:
                kwargs = ast.literal_eval(task['kwargs'])
                if task['name'] == "deployment.tasks.build_hg":
                    build = Build.objects.get(id=int(kwargs['build_id']))
                    app = build.app
                    desc = 'hg build of ' + app.name
                    out.append({'id': task['id'], 'desc': desc})
                elif task['name'] == 'deployment.tasks.deploy':
                    release = Release.objects.get(id=int(kwargs['release_id']))
                    kwargs['appname'] = release.build.app.name
                    desc = '%(appname)s deploy to %(host)s:%(port)s' % kwargs
                    out.append({'id': task['id'], 'desc': desc})

    return json_response({'tasks': out})


@login_required
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


@login_required
def build_hg(request):
    form = forms.BuildForm(request.POST or None)
    if form.is_valid():
        app = App.objects.get(id=form.cleaned_data['app_id'])
        build = Build(app=app, tag=form.cleaned_data['tag'])
        build.save()
        tasks.build_hg.delay(build.id)
        remember('build', 'built %s-%s' % (app.name, build.tag),
                request.user.username)
        return redirect('dash')
    btn_text = "Build"
    return render(request, 'basic_form.html', vars())


@login_required
def upload_build(request):
    form = forms.BuildUploadForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        # process the form and redirect
        form.save()
        # set a message
        remember('build', 'uploaded build %s' % str(form.instance.file),
                 request.user.username)
        # Redirect to the 'deploy' page.
        return HttpResponseRedirect(reverse('deploy'))
    enctype = "multipart/form-data"
    instructions = """Use this form to upload a build.  A valid build should have
    a Procfile, and have all app-specific dependencies already compiled into
    the env."""
    btn_text = 'Upload'
    return render(request, 'basic_form.html', vars())


@login_required
def release(request):
    form = forms.ReleaseForm(request.POST or None)
    if form.is_valid():
        build=Build.objects.get(id=form.cleaned_data['build_id'])
        profile = Profile.objects.get(id=form.cleaned_data['profile_id'])
        r = Release(
            profile=profile,
            build=build,
            config=profile.to_yaml(),
        )
        r.save()
        remember('release', 'created release %s' % r.__unicode__(),
                 request.user.username)
        return HttpResponseRedirect(reverse('deploy'))
    btn_text = 'Save'
    return render(request, 'basic_form.html', vars())


@login_required
def deploy(request):
    # will need a form that lets you create a new deployment.
    form = forms.DeploymentForm(request.POST or None)

    if form.is_valid():
        # We made the form fields exactly match the arguments to the celery
        # task, so we can just use that dict for kwargs
        data = copy.copy(form.cleaned_data)
        data['user'], data['password'] = get_creds(request)

        release = Release.objects.get(id=form.cleaned_data['release_id'])
        data['profile_name'] = release.profile.name
        job = tasks.deploy.delay(**data)
        logging.info('started job %s' % str(job))
        form.cleaned_data['release'] = str(release)
        msg = ('deployed %(release)s-%(proc)s-%(port)s to %(host)s' %
               form.cleaned_data)
        remember('deployment', msg, request.user.username)
        return redirect('dash')

    return render(request, 'basic_form.html', vars())


def get_or_create_release(profile, tag):
    # If there's a release linked to the given profile, that uses the given
    # build, and has current config, then return that.  Else make a new release
    # that satisfies those constraints, and return that.
    releases = Release.objects.filter(profile=profile,
                                      build__tag=tag)

    # XXX This relies on the Releases model having ordering set to '-id'
    if releases and releases[0].parsed_config() == profile.assemble():
        return releases[0]

    # If we got here, there's no existing release with the specified profile,
    # tag, and current config.  Is there at least a build?
    builds = Build.objects.filter(app=profile.app, tag=tag)
    if builds:
        build = builds[0]
    else:
        # Save a build record.  The actual building will be done later.
        build = Build(app=profile.app, tag=tag)
        build.save()
    release = Release(profile=profile, build=build,
                      config=profile.to_yaml())
    release.save()
    return release


@login_required
def edit_swarm(request, swarm_id=None):
    if swarm_id:
        # Need to populate form from swarm
        swarm = Swarm.objects.get(id=swarm_id)
        initial = {
            'profile_id': swarm.profile.id,
            'squad_id': swarm.squad.id,
            'tag': swarm.release.build.tag,
            'proc_name': swarm.proc_name,
            'size': swarm.size,
            'pool': swarm.pool,
            'active': swarm.active
        }
    else:
        initial = None
        swarm = Swarm()

    form = forms.SwarmForm(request.POST or None, initial=initial)
    if form.is_valid():
        data = form.cleaned_data
        swarm.profile = Profile.objects.get(id=data['profile_id'])
        swarm.squad = Squad.objects.get(id=data['squad_id'])
        swarm.proc_name = data['proc_name']
        swarm.size = data['size']
        swarm.pool = data['pool']
        swarm.active = data['active']

        swarm.release = get_or_create_release(swarm.profile, data['tag'])

        swarm.save()
        user, password = get_creds(request)
        tasks.swarm_start.delay(swarm.id, user, password)

        # TODO redirect to tasks page where you can watch progress.
        return redirect(reverse('edit_swarm', kwargs={'swarm_id':swarm.id}))

    # If we're here, and 
    btn_text = 'Swarm'
    return render(request, 'basic_form.html', vars())


def login(request):
    form = forms.LoginForm(request.POST or None)
    if form.is_valid():
        # log the person in.
        django_login(request, form.user)
        # remember creds in session so they can be used for fabric tasks
        # TODO: actually use some encryption on this so an eavesdropper can't
        # harvest creds.  (Though SSL helps already.)
        request.session['creds'] = base64.b64encode('%(username)s:%(password)s'
                                                    % request.POST)
        # redirect to next or home
        return HttpResponseRedirect(request.GET.get('next', '/'))
    hide_nav = True
    return render(request, 'login.html', vars())


def logout(request):
    django_logout(request)
    return HttpResponseRedirect('/')
