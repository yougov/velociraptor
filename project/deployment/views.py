import logging

from django.conf import settings
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404


from deployment import forms, tasks, models, utils


@login_required
def dash(request):
    return render(request, 'dash.html', {
        'hosts': models.Host.objects.filter(active=True),
        'apps': models.App.objects.all(),
        'supervisord_web_port': settings.SUPERVISORD_WEB_PORT
    })


@login_required
def build_hg(request):
    form = forms.BuildForm(request.POST or None)
    if form.is_valid():
        app = models.App.objects.get(id=form.cleaned_data['app_id'])
        build = models.Build(app=app, tag=form.cleaned_data['tag'])
        build.save()
        tasks.build_hg.delay(build_id=build.id)
        models.remember('build', 'built %s-%s' % (app.name, build.tag),
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
        models.remember('build', 'uploaded build %s' % str(form.instance.file),
                 request.user.username)
        # Redirect to the 'deploy' page.
        return HttpResponseRedirect(reverse('deploy'))
    enctype = "multipart/form-data"
    instructions = """Use this form to upload a build.  A valid build should
    have a Procfile, and have all app-specific dependencies already compiled
    into the env."""
    btn_text = 'Upload'
    return render(request, 'basic_form.html', vars())


@login_required
def release(request):
    form = forms.ReleaseForm(request.POST or None)
    if form.is_valid():
        build = models.Build.objects.get(id=form.cleaned_data['build_id'])
        recipe = models.ConfigRecipe.objects.get(id=form.cleaned_data['recipe_id'])
        r = models.Release(
            recipe=recipe,
            build=build,
            config=recipe.to_yaml(),
        )
        r.save()
        models.remember('release', 'created release %s' % r.__unicode__(),
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

        release = models.Release.objects.get(id=data['release_id'])
        job = tasks.deploy.delay(release_id=data['release_id'],
                                 recipe_name=release.recipe.name,
                                 hostname=data['hostname'],
                                 proc=data['proc'],
                                 port=data['port'])
        logging.info('started job %s' % str(job))
        form.cleaned_data['release'] = str(release)
        msg = ('deployed %(release)s-%(proc)s-%(port)s to %(hostname)s' %
               form.cleaned_data)
        models.remember('deployment', msg, request.user.username)
        return redirect('dash')

    return render(request, 'basic_form.html', vars())


def get_or_create_release(recipe, tag):
    # If there's a release linked to the given recipe, that uses the given
    # build, and has current config, then return that.  Else make a new release
    # that satisfies those constraints, and return that.
    releases = models.Release.objects.filter(recipe=recipe,
                                      build__tag=tag)

    # XXX This relies on the Releases model having ordering set to '-id'
    if releases and releases[0].parsed_config() == recipe.assemble():
        return releases[0]

    # If we got here, there's no existing release with the specified recipe,
    # tag, and current config.  Is there at least a build?
    builds = models.Build.objects.filter(app=recipe.app, tag=tag)
    if builds:
        build = builds[0]
    else:
        # Save a build record.  The actual building will be done later.
        build = models.Build(app=recipe.app, tag=tag)
        build.save()
    release = models.Release(recipe=recipe, build=build,
                      config=recipe.to_yaml())
    release.save()
    return release


@login_required
def edit_swarm(request, swarm_id=None):
    if swarm_id:
        # Need to populate form from swarm
        swarm = models.Swarm.objects.get(id=swarm_id)
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
        swarm = models.Swarm()

    form = forms.SwarmForm(request.POST or None, initial=initial)
    if form.is_valid():
        data = form.cleaned_data
        swarm.recipe = models.ConfigRecipe.objects.get(id=data['recipe_id'])
        swarm.squad = models.Squad.objects.get(id=data['squad_id'])
        swarm.proc_name = data['proc_name']
        swarm.size = data['size']
        swarm.pool = data['pool'] or None
        swarm.active = data['active']

        swarm.release = get_or_create_release(swarm.recipe, data['tag'])

        swarm.save()
        tasks.swarm_start.delay(swarm.id)

        models.remember('swarm', 'swarmed %s' % swarm,
                request.user.username)

        return redirect('dash')

    btn_text = 'Swarm'
    return render(request, 'basic_form.html', vars())


@login_required
def edit_squad(request, squad_id=None):
    if squad_id:
        squad = models.Squad.objects.get(id=squad_id)
        # Look up all hosts in the squad
        initial = {
            'name': squad.name,
            'balancer': squad.balancer,
        }
    else:
        squad = models.Squad()
        initial = {}
    form = forms.SquadForm(request.POST or None, initial=initial)
    if form.is_valid():
        # Save the squad
        form.save()
        squad = form.instance
        models.remember('squad', 'saved squad %s' % squad.name, request.user.username)
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


def get_latest_tag(request, recipe_id):
    """ Get the latest tag from the repo, we navigate from the given recipe
    to the app.
    """
    recipe = get_object_or_404(models.ConfigRecipe, pk=recipe_id)
    tags = []
    for tag in recipe.app.tag_set.all():
        tags.append(tag.name)
    return utils.json_response(tags)


def preview_recipe(request, recipe_id):
    """ Preview a settings.yaml generated from a recipe as it is stored in
    the db.
    """
    recipe = get_object_or_404(models.ConfigRecipe, pk=recipe_id)
    return HttpResponse(recipe.to_yaml())


def preview_recipe_addchange(request):
    """ Preview a recipe from the add/change view which will use the currently
    selected ingredients from the inline form (respecting the ones marked for
    delete!)
    """
    # We use a new empty ConfigRecipe to build this preview since we could be
    # adding a new one.
    recipe = models.ConfigRecipe()
    custom_ingredients = []
    # TODO: Collect the custom ingredients from request.GET
    custom_dict = recipe.assemble(custom_ingredients=custom_ingredients)
    return HttpResponse(recipe.to_yaml(custom_dict=custom_dict))


def preview_ingredient(request, recipe_id, ingredient_id):
    """ Preview a recipe from an ingredient change view which will use a
    given recipe ingredients except for the ingredient that is being edited,
    for that it will use the current form value.
    """
    recipe = get_object_or_404(models.ConfigRecipe, pk=recipe_id)
    # Get the current ingredients except for the one we are editing now
    custom_ingredients = [i.ingredient for i in
            models.RecipeIngredient.objects.filter(recipe=recipe).exclude(
                ingredient__id=ingredient_id)]
    custom_dict = recipe.assemble(custom_ingredients=custom_ingredients)
    # Add to the custom dict the values that are being edited
    # TODO: add the logic to get the custom value from request.GET
    custom_value = None
    custom_dict.update(custom_value)
    return HttpResponse(recipe.to_yaml(custom_dict=custom_dict))
