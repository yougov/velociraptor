import ast
import datetime
import json
import logging
import xmlrpclib

from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404

from celery.result import AsyncResult
from celery.task.control import inspect

from djcelery.models import TaskState

from deployment import forms
from deployment import tasks
from deployment.models import (Host, App, Release, Build, ConfigRecipe, Squad,
                               Swarm, remember)


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


@login_required
def api_host_proc(request, host, proc):
    """Display status of a single supervisord-managed process on a host, in JSON"""
    server = xmlrpclib.Server('http://%s:%s' % (host, settings.SUPERVISOR_PORT))
    if request.method == 'GET':
        state = server.supervisor.getProcessInfo(proc)
    elif request.method == 'DELETE':
        # Do proc deletions syncronously instead of with Celery, since they're
        # fast and we want instant feedback.
        tasks.delete_proc(host, proc)
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


def get_task_status(task_id):
    """
    Given a task ID, return a dictionary with status information.
    """
    task = AsyncResult(task_id)
    status = {
        'successful': task.successful(),
        'result': str(task.result), # task.result can be any picklable python object.
        'status': task.status,
        'ready': task.ready(),
        'failed': task.failed(),
        #'name': task.task_name, # this always seems to be empty
    }

    if task.failed():
        status['traceback'] = task.traceback
    return status



def clean_task_value(v):
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    elif isinstance(v, (basestring, int, float, tuple, list, dict, bool,
                        type(None))):
        return v


def task_to_dict(task):
    """
    Given a Celery TaskState instance, return a JSONable dict with its
    information.
    """
    # Make a copy of task.__dict__, leaving off any of the cached complex
    # objects
    return {k:clean_task_value(v) for k, v in task.__dict__.items() if not
           k.startswith('_')}


@login_required
def api_task_recent(request):

    count = int(request.GET.get('count') or 20)
    tasks = TaskState.objects.all()[:count]

    return json_response({'tasks': [task_to_dict(t) for t in tasks]})


@login_required
def api_task_status(request, task_id):
    status = get_task_status(task_id)
    status['id'] = task_id

    return json_response(status)


@login_required
def build_hg(request):
    form = forms.BuildForm(request.POST or None)
    if form.is_valid():
        app = App.objects.get(id=form.cleaned_data['app_id'])
        build = Build(app=app, tag=form.cleaned_data['tag'])
        build.save()
        tasks.build_hg.delay(build_id=build.id)
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
        recipe = ConfigRecipe.objects.get(id=form.cleaned_data['recipe_id'])
        r = Release(
            recipe=recipe,
            build=build,
            config=recipe.to_yaml(),
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
        data = form.cleaned_data

        release = Release.objects.get(id=data['release_id'])
        job = tasks.deploy.delay(release_id=data['release_id'],
                                 recipe_name=release.recipe.name,
                                 hostname=data['hostname'],
                                 proc=data['proc'],
                                 port=data['port'])
        logging.info('started job %s' % str(job))
        form.cleaned_data['release'] = str(release)
        msg = ('deployed %(release)s-%(proc)s-%(port)s to %(hostname)s' %
               form.cleaned_data)
        remember('deployment', msg, request.user.username)
        return redirect('dash')

    return render(request, 'basic_form.html', vars())


def get_or_create_release(recipe, tag):
    # If there's a release linked to the given recipe, that uses the given
    # build, and has current config, then return that.  Else make a new release
    # that satisfies those constraints, and return that.
    releases = Release.objects.filter(recipe=recipe,
                                      build__tag=tag)

    # XXX This relies on the Releases model having ordering set to '-id'
    if releases and releases[0].parsed_config() == recipe.assemble():
        return releases[0]

    # If we got here, there's no existing release with the specified recipe,
    # tag, and current config.  Is there at least a build?
    builds = Build.objects.filter(app=recipe.app, tag=tag)
    if builds:
        build = builds[0]
    else:
        # Save a build record.  The actual building will be done later.
        build = Build(app=recipe.app, tag=tag)
        build.save()
    release = Release(recipe=recipe, build=build,
                      config=recipe.to_yaml())
    release.save()
    return release


@login_required
def edit_swarm(request, swarm_id=None):
    if swarm_id:
        # Need to populate form from swarm
        swarm = Swarm.objects.get(id=swarm_id)
        initial = {
            'recipe_id': swarm.recipe.id,
            'squad_id': swarm.squad.id,
            'tag': swarm.release.build.tag,
            'proc_name': swarm.proc_name,
            'size': swarm.size,
            'pool': swarm.pool or '',
            'active': swarm.active
        }
    else:
        initial = None
        swarm = Swarm()

    form = forms.SwarmForm(request.POST or None, initial=initial)
    if form.is_valid():
        data = form.cleaned_data
        swarm.recipe = ConfigRecipe.objects.get(id=data['recipe_id'])
        swarm.squad = Squad.objects.get(id=data['squad_id'])
        swarm.proc_name = data['proc_name']
        swarm.size = data['size']
        swarm.pool = data['pool'] or None
        swarm.active = data['active']

        swarm.release = get_or_create_release(swarm.recipe, data['tag'])

        swarm.save()
        tasks.swarm_start.delay(swarm.id)

        return redirect('dash')

    # If we're here, and
    btn_text = 'Swarm'
    return render(request, 'basic_form.html', vars())


def login(request):
    form = forms.LoginForm(request.POST or None)
    if form.is_valid():
        # log the person in.
        django_login(request, form.user)
        # redirect to next or home
        return HttpResponseRedirect(request.GET.get('next', '/'))
    hide_nav = True
    return render(request, 'login.html', vars())


def logout(request):
    django_logout(request)
    return HttpResponseRedirect('/')

def preview_recipe(request, recipe_id):
    """ Preview a settings.yaml generated from a recipe as it is stored in
    the db.
    """
    recipe = get_object_or_404(ConfigRecipe, pk=recipe_id)
    return HttpResponse(recipe.to_yaml())

def preview_recipe_addchange(request, recipe_id):
    """ Preview a recipe from the add/change view which will use the currently
    selected ingredients from the inline form (respecting the ones marked for
    delete!)
    """
    recipe = get_object_or_404(ConfigRecipe, pk=recipe_id)
    custom_ingredients = []
    # TODO: Collect the custom ingredients from request.GET
    custom_dict = recipe.assemble(custom_ingredients=custom_ingredients)
    return HttpResponse(recipe.to_yaml(custom_dict=custom_dict))

def preview_recipe_from_ingredient(request, recipe_id, ingredient_id):
    """ Preview a recipe from an ingredient change view which will use a
    given recipe ingredients except for the ingredient that is being edited,
    for that it will use the current form value.
    """
    recipe = get_object_or_404(ConfigRecipe, pk=recipe_id)
    # Get the current ingredients except for the one we are editing now
    custom_ingredients = [i.ingredient for i in
            RecipeIngredient.objects.filter(recipe=recipe).exclude(
                ingredient__id=ingredient_id)]
    custom_dict = recipe.assemble(custom_ingredients=custom_ingredients)
    # Add to the custom dict the values that are being edited
    # TODO: add the logic to get the custom value from request.GET
    custom_value = None
    custom_dict.update(custom_value)
    return HttpResponse(recipe.to_yaml(custom_dict=custom_dict))
