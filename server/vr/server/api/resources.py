from __future__ import print_function

import json

from django.conf.urls.defaults import url
from django.http import (HttpResponse, HttpResponseNotAllowed,
                         HttpResponseNotFound)
from django.contrib.auth.models import User

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import authentication as auth
from tastypie.authorization import Authorization
from tastypie.api import Api
from tastypie.constants import ALL_WITH_RELATIONS, ALL
from tastypie.utils import trailing_slash

from vr.server import models
from vr.server.views import do_swarm, do_build, do_deploy
from vr.server.api.views import auth_required


# XXX Note that procs don't have a resource in this file.  It turns out that
# Tastypie is not as good at handling non-ORM resources as I was led to
# believe.  I made an effort, and ended up getting it mostly working, but it
# was ugly as hell and using tons of subclasses and overrides.  In the end I
# decided to just write a Django view and hard-code a route to
# /api/v1/hosts/<name>/procs/. --Brent

v1 = Api(api_name='v1')


class SquadResource(ModelResource):
    hosts = fields.ToManyField('api.resources.HostResource', 'hosts',
                               full=True)

    class Meta:
        queryset = models.Squad.objects.all()
        resource_name = 'squads'
        filtering = {
            'hosts': ALL_WITH_RELATIONS,
        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
        detail_uri_name = 'name'
v1.register(SquadResource())


class IngredientResource(ModelResource):
    swarms = fields.ToManyField('api.resources.SwarmResource', 'swarms',
                                blank=True, null=True, readonly=True)

    class Meta:
        queryset = models.ConfigIngredient.objects.all()
        filtering = {
            'name': ALL,
        }
        resource_name = 'ingredients'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(IngredientResource())


class AppResource(ModelResource):

    class Meta:
        queryset = models.App.objects.all()
        resource_name = 'apps'
        filtering = {
            'name': ALL,
        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
        detail_uri_name = 'name'
v1.register(AppResource())


class BuildPackResource(ModelResource):
    class Meta:
        queryset = models.BuildPack.objects.all()
        resource_name = 'buildpacks'
        filtering = {
            'repo_url': ALL,
            'repo_type': ALL,
        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(BuildPackResource())


class BuildResource(ModelResource):
    app = fields.ToOneField('api.resources.AppResource', 'app')
    class Meta:
        queryset = models.Build.objects.all()
        resource_name = 'builds'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/build%s$" %
                (self._meta.resource_name, trailing_slash()),
                auth_required(self.wrap_view('do_build')), name="api_do_build"),
        ]

    def do_build(self, request, **kwargs):

        if request.method == 'POST':
            try:
                build = models.Build.objects.get(id=int(kwargs['pk']))
            except models.Build.DoesNotExist:
                return HttpResponseNotFound()

            do_build(build, request.user)

            # Status 202 means "The request has been accepted for processing, but
            # the processing has not been completed."
            return HttpResponse(status=202)

        return HttpResponseNotAllowed(["POST"])
v1.register(BuildResource())


class SwarmResource(ModelResource):
    app = fields.ToOneField('api.resources.AppResource', 'app')
    squad = fields.ToOneField('api.resources.SquadResource', 'squad')

    # Leave 'release' blank when you want to set 'version' to something new, and
    # the model will intelligently create a new release for you.
    release = fields.ToOneField('api.resources.ReleaseResource', 'release',
        blank=True, null=True)

    shortname = fields.CharField('shortname')
    volumes = fields.ListField('volumes', null=True)
    config_ingredients = fields.ToManyField('api.resources.IngredientResource',
                                           'config_ingredients')
    compiled_config = fields.DictField('get_config')
    compiled_env = fields.DictField('get_env')
    version = fields.CharField('version')

    class Meta:
        queryset = models.Swarm.objects.all()
        resource_name = 'swarms'
        filtering = {
            'ingredients': ALL_WITH_RELATIONS,
            'squad': ALL_WITH_RELATIONS,
            'app': ALL_WITH_RELATIONS,
            'proc_name': ALL,
            'config_name': ALL,

        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()

    def dehydrate(self, bundle):
        # add in proc data
        # TODO: Make these proper attributes so they can be saved by a PUT/POST
        # to the swarm resource.
        bundle.data['procs_uri'] = bundle.data['resource_uri'] + 'procs/'
        bundle.data['procs'] = [p.as_dict() for p in
                                bundle.obj.get_procs(check_cache=True)]
        bundle.data['squad_name'] = bundle.obj.squad.name

        # Also add in convenience data
        bundle.data.update(app_name=bundle.obj.app.name,
                           config_name=bundle.obj.config_name)
        return bundle

    def hydrate(self, bundle):
        # delete the compiled_config and compiled_env keys in the bundle, because
        # they can cause hydration problems if tastypie tries to set them.
        bundle.data.pop('compiled_config', None)
        bundle.data.pop('compiled_env', None)

        # If version is provided, that takes priority over release
        if 'version' in bundle.data:
            bundle.data.pop('release', None)
        return bundle

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/swarm%s$" %
                (self._meta.resource_name, trailing_slash()),
                auth_required(self.wrap_view('do_swarm')), name="api_do_swarm"),
        ]

    def do_swarm(self, request, **kwargs):

        if request.method == 'POST':
            try:
                swarm = models.Swarm.objects.get(id=int(kwargs['pk']))
            except models.Swarm.DoesNotExist:
                return HttpResponseNotFound()

            do_swarm(swarm, request.user)

            # Status 202 means "The request has been accepted for processing, but
            # the processing has not been completed."
            return HttpResponse(status=202)

        return HttpResponseNotAllowed(["POST"])
v1.register(SwarmResource())


class ReleaseResource(ModelResource):
    build = fields.ToOneField('api.resources.BuildResource', 'build')

    class Meta:
        queryset = models.Release.objects.all()
        resource_name = 'releases'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/deploy%s$" %
                (self._meta.resource_name, trailing_slash()),
                auth_required(self.wrap_view('deploy_release')),
                name="api_deploy_release"),
        ]

    def deploy_release(self, request, **kwargs):
        if request.method != 'POST':
            return HttpResponseNotAllowed(["POST"])

        try:
            release = models.Release.objects.get(id=int(kwargs['pk']))
        except models.Swarm.DoesNotExist:
            return HttpResponseNotFound()

        data = json.loads(request.raw_post_data)
        print("data", data)
        do_deploy(release, request.user, data['config_name'], data['host'],
                  data['proc'], data['port'])

        # Status 202 means "The request has been accepted for processing, but
        # the processing has not been completed."
        return HttpResponse(status=202)

v1.register(ReleaseResource())


class TestResultResource(ModelResource):
    testrun = fields.ToOneField('api.resources.TestRunResource', 'run',
                                related_name='tests')

    class Meta:
        queryset = models.TestResult.objects.all()
        resource_name = 'testresults'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(TestResultResource())


class TestRunResource(ModelResource):
    testresults = fields.ToManyField('api.resources.TestResultResource',
                                     'tests', full=True)

    class Meta:

        queryset = models.TestRun.objects.all()
        resource_name = 'testruns'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(TestRunResource())


class HostResource(ModelResource):
    squad = fields.ToOneField('api.resources.SquadResource', 'squad')

    class Meta:
        queryset = models.Host.objects.all()
        resource_name = 'hosts'
        filtering = {
            'name': ALL,
        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
        detail_uri_name = 'name'

    def dehydrate(self, bundle):
        bundle.data['procs_uri'] = bundle.data['resource_uri'] + 'procs/'
        bundle.data['procs'] = [p.as_dict() for p in
                                bundle.obj.get_procs(check_cache=True)]
        return bundle
v1.register(HostResource())


class LogResource(ModelResource):
    user = fields.ToOneField('api.resources.UserResource', 'user', full=True)

    class Meta:
        queryset = models.DeploymentLogEntry.objects.all()
        resource_name = 'logs'
        filtering = {
            'type': ALL,
            'time': ALL,
            'user': ALL_WITH_RELATIONS,
            'message': ALL,
        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(LogResource())

class UserResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        excludes = ['email', 'password', 'is_active', 'is_staff', 'is_superuser']
        filtering = {
            'username': ALL,
        }
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(UserResource())
