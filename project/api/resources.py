from tastypie.resources import ModelResource
from tastypie import fields
from tastypie import authentication as auth
from tastypie.authorization import Authorization
from tastypie.api import Api
from tastypie.constants import ALL_WITH_RELATIONS, ALL

from deployment import models


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


class RecipeResource(ModelResource):
    ingredients = fields.ToManyField('api.resources.IngredientResource',
                                     'ingredients')
    app = fields.ToOneField('api.resources.AppResource', 'app')

    class Meta:
        queryset = models.ConfigRecipe.objects.all()
        resource_name = 'recipes'
        filtering = {
            'app': ALL_WITH_RELATIONS,
            'name': ALL,
        }
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
    recipe = fields.ToOneField('api.resources.RecipeResource', 'recipe')
    squad = fields.ToOneField('api.resources.SquadResource', 'squad')
    release = fields.ToOneField('api.resources.ReleaseResource', 'release')

    shortname = fields.CharField('shortname')

    class Meta:
        queryset = models.Swarm.objects.all()
        resource_name = 'swarms'
        filtering = {
            'recipe': ALL_WITH_RELATIONS,
            'squad': ALL_WITH_RELATIONS,
            'proc_name': ALL,

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
        bundle.data.update(app_name=bundle.obj.recipe.app.name,
                           recipe_name=bundle.obj.recipe.name)
        return bundle
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
