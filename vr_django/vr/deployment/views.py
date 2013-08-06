import logging
import textwrap

from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.generic import edit
from django.views.generic import ListView

from vr.deployment import forms, tasks, models, events
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

        do_swarm(swarm, request.user)

        return redirect('dash')

    return render(request, 'swarm.html', {
        'swarm': swarm,
        'form': form,
        'btn_text': 'Swarm',
    })


def do_swarm(swarm, user):
    """
    Put a swarming job on the queue, and a notification about it on the pubsub.
    """
    tasks.swarm_start.delay(swarm.id)
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
        """) % {
            'user': user.username,
            'shortname': swarm.shortname(),
            'app': swarm.app,
            'tag': swarm.release.build.tag,
            'config_name': swarm.config_name,
            'proc_name': swarm.proc_name,
            'squad': swarm.squad,
            'size': swarm.size,
            'balancer': swarm.balancer,
            'pool': swarm.pool,
        }
    events.eventify(user, 'swarm', swarm.shortname(),
                    detail=ev_detail)



class ListLogEntry(ListView):
    template_name = 'log.html'
    model = models.DeploymentLogEntry
    paginate_by = 50


class UpdateConfigIngredient(edit.UpdateView):
    template_name = 'ingredient_form.html'
    model = models.ConfigIngredient
    success_url = reverse_lazy('ingredient_list')
    form_class = forms.ConfigIngredientForm


class AddConfigIngredient(edit.CreateView):
    template_name = 'ingredient_form.html'
    model = models.ConfigIngredient
    success_url = reverse_lazy('ingredient_list')
    form_class = forms.ConfigIngredientForm


class ListConfigIngredient(ListView):
    template_name = 'ingredient_list.html'
    model = models.ConfigIngredient
    paginate_by = 30


class DeleteConfigIngredient(edit.DeleteView):
    model = models.ConfigIngredient
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('ingredient_list')


class ListHost(ListView):
    model = models.Host
    template_name = 'host_list.html'


class AddHost(edit.CreateView):
    template_name = 'host_form.html'
    model = models.Host
    success_url = reverse_lazy('host_list')
    form_class = forms.HostForm


class UpdateHost(edit.UpdateView):
    template_name = 'host_form.html'
    model = models.Host
    success_url = reverse_lazy('host_list')
    form_class = forms.HostForm


class DeleteHost(edit.DeleteView):
    model = models.Host
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('host_list')


class ListSquad(ListView):
    model = models.Squad
    template_name = 'squad_list.html'


class AddSquad(edit.CreateView):
    template_name = 'squad_form.html'
    model = models.Squad
    success_url = reverse_lazy('squad_list')
    form_class = forms.SquadForm


class UpdateSquad(edit.UpdateView):
    template_name = 'squad_form.html'
    model = models.Squad
    success_url = reverse_lazy('squad_list')
    form_class = forms.SquadForm


class DeleteSquad(edit.DeleteView):
    model = models.Squad
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('squad_list')


class ListApp(ListView):
    model = models.App
    template_name = 'app_list.html'


class AddApp(edit.CreateView):
    template_name = 'app_form.html'
    model = models.App
    success_url = reverse_lazy('app_list')


class UpdateApp(edit.UpdateView):
    template_name = 'app_form.html'
    model = models.App
    success_url = reverse_lazy('app_list')


class DeleteApp(edit.DeleteView):
    model = models.App
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('app_list')


class ListBuildPack(ListView):
    model = models.BuildPack
    template_name = 'buildpack_list.html'


class AddBuildPack(edit.CreateView):
    template_name = 'buildpack_form.html'
    model = models.BuildPack
    success_url = reverse_lazy('buildpack_list')


class UpdateBuildPack(edit.UpdateView):
    template_name = 'buildpack_form.html'
    model = models.BuildPack
    success_url = reverse_lazy('buildpack_list')


class DeleteBuildPack(edit.DeleteView):
    model = models.BuildPack
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('buildpack_list')


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
