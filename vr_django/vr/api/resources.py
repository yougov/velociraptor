from django.conf.urls.defaults import url
from django.http import HttpResponse, HttpResponseNotAllowed

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import authentication as auth
from tastypie.authorization import Authorization
from tastypie.api import Api
from tastypie.constants import ALL_WITH_RELATIONS, ALL
from tastypie.utils import trailing_slash

from vr.deployment import models
from vr.api.views import auth_required


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
    swarms = fields.ToManyField('api.resources.SwarmResource', 'swarms')

    class Meta:
        queryset = models.ConfigIngredient.objects.all()
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
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(BuildPackResource())


class BuildResource(ModelResource):
    class Meta:
        queryset = models.Build.objects.all()
        resource_name = 'builds'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(BuildResource())


class SwarmResource(ModelResource):
    app = fields.ToOneField('api.resources.AppResource', 'app')
    squad = fields.ToOneField('api.resources.SquadResource', 'squad')
    release = fields.ToOneField('api.resources.ReleaseResource', 'release')

    shortname = fields.CharField('shortname')
    config_ingredients = fields.ToManyField('api.resources.IngredientResource',
                                           'config_ingredients')
    compiled_config = fields.DictField('get_config')
    compiled_env = fields.DictField('get_env')

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
        bundle.data['version'] = bundle.obj.release.build.tag

        # Also add in convenience data
        bundle.data.update(app_name=bundle.obj.app.name,
                           config_name=bundle.obj.config_name)
        return bundle

    def prepend_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/go%s$" %
                (self._meta.resource_name, trailing_slash()),
                auth_required(self.wrap_view('do_swarm')), name="api_do_swarm"),
        ]

    def do_swarm(self, request, **kwargs):

        if request.method == 'POST':
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
                                     'tests')

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
