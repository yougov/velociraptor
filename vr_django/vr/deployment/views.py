import logging

from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404


from vr.deployment import forms, tasks, models, events, utils
from vr.deployment.utils import yamlize


@login_required
def dash(request):
    return render(request, 'dash.html', {
        'hosts': models.Host.objects.filter(active=True),
        'apps': models.App.objects.all(),
        'supervisord_web_port': settings.SUPERVISORD_WEB_PORT
    })


@login_required
def build_app(request):
    form = forms.BuildForm(request.POST or None)
    if form.is_valid():
        app = models.App.objects.get(id=form.cleaned_data['app_id'])
        build = models.Build(app=app, tag=form.cleaned_data['tag'])
        build.save()
        tasks.build_app.delay(build_id=build.id)
        events.eventify(request.user, 'build', build)
        return redirect('dash')
    return render(request, 'basic_form.html', {
        'form': form,
        'btn_text': 'Build',
    })


@login_required
def upload_build(request):
    form = forms.BuildUploadForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        events.eventify(request.user, 'upload', form.instance)
        return HttpResponseRedirect(reverse('deploy'))

    return render(request, 'basic_form.html', {
        'form': form,
        'btn_text': 'Upload',
        'instructions': """Use this form to upload a build.  A valid build
        should have a Procfile, and have all app-specific dependencies already
        compiled into the env.""",
        'enctype': "multipart/form-data"
    })


@login_required
def release(request):
    form = forms.ReleaseForm(request.POST or None)
    if form.is_valid():
        # Take the env vars from the build, update with vars from the form, and
        # save on the instance.
        release = form.instance
        env_yaml = release.build.env_yaml or {}
        env_yaml.update(release.env_yaml or {})
        release.env_yaml = env_yaml
        form.save()
        events.eventify(request.user, 'release', release)
        return HttpResponseRedirect(reverse('deploy'))
    return render(request, 'basic_form.html', {
        'form': form,
        'btn_text': 'Save',
    })


@login_required
def deploy(request):
    # will need a form that lets you create a new deployment.
    form = forms.DeploymentForm(request.POST or None, initial={'contain': True})

    if form.is_valid():
        # We made the form fields exactly match the arguments to the celery
        # task, so we can just use that dict for kwargs
        data = form.cleaned_data

        release = models.Release.objects.get(id=data['release_id'])
        job = tasks.deploy.delay(release_id=data['release_id'],
                                 config_name=data['config_name'],
                                 hostname=data['hostname'],
                                 proc=data['proc'],
                                 port=data['port'],
                                 contain=data['contain'])
        logging.info('started job %s' % str(job))
        form.cleaned_data['release'] = str(release)
        proc = '%(release)s-%(proc)s-%(port)s to %(hostname)s' % data
        events.eventify(request.user, 'deploy', proc)
        return redirect('dash')

    return render(request, 'basic_form.html', vars())


@login_required
def proclog(request, hostname, procname):
    return render(request, 'proclog.html', vars())


@login_required
def edit_swarm(request, swarm_id=None):
    if swarm_id:
        # Need to populate form from swarm
        swarm = models.Swarm.objects.get(id=swarm_id)
        initial = {
            'app_id': swarm.app.id,
            'squad_id': swarm.squad.id,
            'tag': swarm.release.build.tag,
            'config_name': swarm.config_name,
            'config_yaml': yamlize(swarm.config_yaml),
            'env_yaml': yamlize(swarm.env_yaml),
            'proc_name': swarm.proc_name,
            'size': swarm.size,
            'pool': swarm.pool or '',
            'balancer': swarm.balancer,
            'config_ingredients': [
                ing.pk for ing in swarm.config_ingredients.all()]
        }
    else:
        initial = None
        swarm = models.Swarm()

    form = forms.SwarmForm(request.POST or None, initial=initial)
    if form.is_valid():
        data = form.cleaned_data
        swarm.app = models.App.objects.get(id=data['app_id'])
        swarm.squad = models.Squad.objects.get(id=data['squad_id'])
        swarm.config_name = data['config_name']
        swarm.config_yaml = data['config_yaml']
        swarm.env_yaml = data['env_yaml']
        swarm.proc_name = data['proc_name']
        swarm.size = data['size']
        swarm.pool = data['pool'] or None
        swarm.balancer = data['balancer'] or None
        swarm.release = swarm.get_current_release(data['tag'])
        swarm.save()
        swarm.config_ingredients.clear()
        for ingredient in data['config_ingredients']:
            swarm.config_ingredients.add(ingredient)
        tasks.swarm_start.delay(swarm.id)
        import textwrap
        ev_data = dict(data)
        ev_data.update(user=request.user.username, app=swarm.app.name,
                       shortname=swarm.shortname(),
                       squad=swarm.squad.name)
        ev_detail = textwrap.dedent(
            """%(user)s swarmed %(shortname)s

            App: %(app)s
            Version: %(tag)s
            Config Name: %(config_name)s
            Proc Name: %(proc_name)s
            Squad: %(squad)s
            Size: %(size)s
            Balancer: %(balancer)s
            Pool: %(pool)s
            """) % ev_data
        events.eventify(request.user, 'swarm', swarm.shortname(),
                        detail=ev_detail)
        return redirect('dash')

    return render(request, 'swarm.html', {
        'swarm': swarm,
        'form': form,
        'btn_text': 'Swarm',
    })


@login_required
def edit_squad(request, squad_id=None):
    if squad_id:
        squad = models.Squad.objects.get(id=squad_id)
        # Look up all hosts in the squad
        initial = {
            'name': squad.name,
        }
    else:
        squad = models.Squad()
        initial = {}
    form = forms.SquadForm(request.POST or None, initial=initial)
    if form.is_valid():
        # Save the squad
        form.save()
        squad = form.instance
        events.eventify(request.user, 'save', squad)
        redirect('edit_squad', squad_id=squad.id)
    return render(request, 'squad.html', {
        'squad': squad,
        'form': form,
        'btn_text': 'Save',
        'docstring': models.Squad.__doc__
    })


def login(request):
    form = forms.LoginForm(request.POST or None)
    if form.is_valid():
        # log the person in.
        django_login(request, form.user)
        # redirect to next or home
        return HttpResponseRedirect(request.GET.get('next', '/'))
    return render(request, 'login.html', {
        'form': form,
        'hide_nav': True
    })


def logout(request):
    django_logout(request)
    return HttpResponseRedirect('/')