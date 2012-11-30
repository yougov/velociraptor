from django.conf.urls.defaults import url

from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import authentication as auth
from tastypie.authorization import Authorization
from tastypie.api import Api

from deployment import models


v1 = Api(api_name='v1')


class NamedModelResource(ModelResource):
    """
    Automatically provides name-based url routes for model-based resources that
    have a 'name' field with a uniqueness constraint.
    """
    def prepend_urls(self):
        return [url(r"^(?P<resource_name>%s)/(?P<name>[\w\d_.-]+)/$" %
                         self._meta.resource_name,
                     self.wrap_view('dispatch_detail'),
                     name="api_dispatch_detail"), ]


class HostResource(NamedModelResource):
    squad = fields.ToOneField('api.resources.SquadResource', 'squad')

    class Meta:
        queryset = models.Host.objects.all()
        resource_name = 'hosts'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(HostResource())


class SquadResource(NamedModelResource):
    hosts = fields.ToManyField('api.resources.HostResource', 'hosts')

    class Meta:
        queryset = models.Squad.objects.all()
        resource_name = 'squads'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(SquadResource())


class RecipeResource(ModelResource):
    ingredients = fields.ToManyField('api.resources.IngredientResource',
                                     'ingredients')
    app = fields.ToOneField('api.resources.AppResource', 'app')

    class Meta:
        queryset = models.ConfigRecipe.objects.all()
        resource_name = 'recipes'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(RecipeResource())


class IngredientResource(ModelResource):
    recipes = fields.ToManyField('api.resources.RecipeResource', 'recipes')

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
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
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
    recipe = fields.ToOneField('api.resources.RecipeResource', 'recipe')
    squad = fields.ToOneField('api.resources.SquadResource', 'squad')
    release = fields.ToOneField('api.resources.ReleaseResource', 'release')

    class Meta:
        queryset = models.Swarm.objects.all()
        resource_name = 'swarms'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(SwarmResource())


class ReleaseResource(ModelResource):
    recipe = fields.ToOneField('api.resources.RecipeResource', 'recipe')
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
    testresults = fields.ToManyField('api.resources.TestResultResource', 'tests')

    class Meta:

        queryset = models.TestRun.objects.all()
        resource_name = 'testruns'
        authentication = auth.MultiAuthentication(
            auth.BasicAuthentication(),
            auth.SessionAuthentication(),
        )
        authorization = Authorization()
v1.register(TestRunResource())
