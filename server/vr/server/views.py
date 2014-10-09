import textwrap

from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import edit
from django.views.generic import ListView
from django.utils import simplejson

from reversion import revision
from reversion.models import Version
from reversion.helpers import generate_patch

from vr.server import forms, tasks, events, models
from vr.server.utils import yamlize


def json_response(func):
    """
    A decorator thats takes a view response and turns it
    into json. If a callback is added through GET or POST
    the response is JSONP.
    """
    def decorator(request, *args, **kwargs):
        objects = func(request, *args, **kwargs)
        if isinstance(objects, HttpResponse):
            return objects
        try:
            data = simplejson.dumps(objects)
            if 'callback' in request.REQUEST:
                # a jsonp response!
                data = '%s(%s);' % (request.REQUEST['callback'], data)
                return HttpResponse(data, "text/javascript")
        except:
            data = simplejson.dumps(str(objects))
        return HttpResponse(data, "application/json")
    return decorator


@login_required
def dash(request):
    return render(request, 'dash.html', {
        'hosts': models.Host.objects.filter(active=True),
        'dashboard_id': '',
        'dashboard_name': 'Home',
        'supervisord_web_port': settings.SUPERVISORD_WEB_PORT
    })

@login_required
def default_dash(request):
    if hasattr(request.user, 'userprofile') and request.user.userprofile:
        dashboard = request.user.userprofile.default_dashboard
        if dashboard is not None:
            dashboard_name = 'Default - %s' % dashboard.name
            return render(request, 'dash.html', {
                'hosts': models.Host.objects.filter(active=True),
                'dashboard_id': dashboard.id,
                'dashboard_name': dashboard_name,
                'supervisord_web_port': settings.SUPERVISORD_WEB_PORT
            })
    # If you don't have a default dashboard go to home!
    return HttpResponseRedirect('/')

@login_required
def custom_dash(request, slug):
    dashboard = get_object_or_404(models.Dashboard, slug=slug)
    return render(request, 'dash.html', {
        'hosts': models.Host.objects.filter(active=True),
        'dashboard_id': dashboard.id,
        'dashboard_name': dashboard.name,
        'supervisord_web_port': settings.SUPERVISORD_WEB_PORT
    })


@login_required
def build_app(request):
    form = forms.BuildForm(request.POST or None)
    if form.is_valid():
        app = models.App.objects.get(id=form.cleaned_data['app_id'])
        os_image_id = form.cleaned_data['os_image_id']
        os_image = models.OSImage.objects.get(id=os_image_id) \
            if os_image_id is not None else None
        build = models.Build(app=app, tag=form.cleaned_data['tag'],
                             os_image=os_image)
        build.save()
        do_build(build, request.user)
        return redirect('dash')
    return render(request, 'basic_form.html', {
        'form': form,
        'btn_text': 'Build',
    })


def do_build(build, user):
    """
    Put a build job on the worker queue, and a notification about it on the
    pubsub.
    """
    tasks.build_app.delay(build_id=build.id)
    events.eventify(user, 'build', build)


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

    builds = models.Build.objects
    form.fields['build'].queryset = builds.filter(status=models.BUILD_SUCCESS)
    return render(request, 'basic_form.html', {
        'form': form,
        'btn_text': 'Save',
    })


@login_required
def deploy(request):
    # will need a form that lets you create a new deployment.
    form = forms.DeploymentForm(request.POST or None)

    if form.is_valid():
        # We made the form fields exactly match the arguments to the celery
        # task, so we can just use that dict for kwargs
        data = form.cleaned_data

        release = models.Release.objects.get(id=data.pop('release_id'))
        do_deploy(release, request.user, **data)
        return redirect('dash')

    return render(request, 'basic_form.html', vars())


def do_deploy(release, user, config_name, hostname, proc, port):
    """
    Put a deploy job on the work queue, and a notification about it on the
    events pubsub.
    """
    tasks.deploy.delay(release_id=release.id, config_name=config_name,
                       hostname=hostname, proc=proc, port=port)
    procname = '%(release)s-%(proc)s-%(port)s to %(hostname)s' % vars()
    events.eventify(user, 'deploy', procname)


@login_required
def proclog(request, hostname, procname):
    return render(request, 'proclog.html', vars())


@login_required
@revision.create_on_success
def edit_swarm(request, swarm_id=None):
    if swarm_id:
        # Need to populate form from swarm
        swarm = models.Swarm.objects.get(id=swarm_id)
        initial = {
            'app_id': swarm.app.id,
            'os_image_id': getattr(swarm.release.build.os_image, 'id', None),
            'squad_id': swarm.squad.id,
            'tag': swarm.release.build.tag,
            'config_name': swarm.config_name,
            'config_yaml': yamlize(swarm.config_yaml),
            'env_yaml': yamlize(swarm.env_yaml),
            'volumes': yamlize(swarm.volumes),
            'run_as': swarm.run_as or 'nobody',
            'mem_limit': swarm.mem_limit,
            'memsw_limit': swarm.memsw_limit,
            'proc_name': swarm.proc_name,
            'size': swarm.size,
            'pool': swarm.pool or '',
            'balancer': swarm.balancer,
            'config_ingredients': [
                ing.pk for ing in swarm.config_ingredients.all()]
        }
        fields = [field for field in swarm._meta.fields]
        version_list = Version.objects.get_for_object(swarm).reverse()
        version_diffs = []
        if len(version_list) > 1:
            for version in version_list[1:6]:
                diff_dict = {}
                for field in fields:
                    diff = generate_patch(version_list[0], version, field.name)
                    if diff:
                        diff_dict[field.name] = version.field_dict[field.name]
                version_diffs.append({'diff_dict': diff_dict,
                                      'user': version.revision.user,
                                      'date': version.revision.date_created})
    else:
        initial = None
        swarm = models.Swarm()
        version_diffs = []

    form = forms.SwarmForm(request.POST or None, initial=initial)
    if form.is_valid():
        data = form.cleaned_data
        os_image = models.OSImage.objects.get(id=data['os_image_id']) \
            if data['os_image_id'] is not None else None

        swarm.app = models.App.objects.get(id=data['app_id'])
        swarm.squad = models.Squad.objects.get(id=data['squad_id'])
        swarm.config_name = data['config_name']
        swarm.config_yaml = data['config_yaml']
        swarm.env_yaml = data['env_yaml']
        swarm.volumes = data['volumes']
        swarm.run_as = data['run_as']
        swarm.mem_limit = data['mem_limit']
        swarm.memsw_limit = data['memsw_limit']
        swarm.proc_name = data['proc_name']
        swarm.size = data['size']
        swarm.pool = data['pool'] or None
        swarm.balancer = data['balancer'] or None
        swarm.release = swarm.get_current_release(os_image, data['tag'])
        swarm.save()
        swarm.config_ingredients.clear()
        for ingredient in data['config_ingredients']:
            swarm.config_ingredients.add(ingredient)
        revision.user = request.user
        revision.comment = "Created from web form."

        do_swarm(swarm, request.user)

        return redirect('dash')

    return render(request, 'swarm.html', {
        'swarm': swarm,
        'form': form,
        'btn_text': 'Swarm',
        'version_diffs': version_diffs
    })


@login_required
@json_response
def search_swarm(request):
    query = request.GET.get('query', None)

    if query:
        swarms = models.Swarm.objects.filter(
            Q(app__name__icontains=query) |
            Q(config_name__icontains=query) |
            Q(release__build__tag__icontains=query) |
            Q(proc_name__icontains=query))
    else:
        swarms = models.Swarm.objects.all()

    return [{
        'shortname': swarm.shortname(),
        'id': swarm.id,
        'app_name': swarm.app.name
    } for swarm in swarms]


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
        Memory: %(memory)s
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
            'memory': swarm.get_memory_limit_str(),
            'size': swarm.size,
            'balancer': swarm.balancer,
            'pool': swarm.pool,
        }
    events.eventify(user, 'swarm', swarm.shortname(),
                    detail=ev_detail, swarm_id=swarm.id)
    return str(swarm)  # this can be used as an trace ID


class ListLogEntry(ListView):
    template_name = 'log.html'
    model = models.DeploymentLogEntry
    paginate_by = 50

    def get_context_data(self, **kwargs):
        context = super(ListLogEntry, self).get_context_data(**kwargs)
        context['apps_list'] = models.App.objects.all()
        context['users_list'] = User.objects.all()
        return context


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
