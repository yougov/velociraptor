import reversion

from django.contrib import admin
from django.contrib.auth.models import Group

from vr.deployment import models
from vr.deployment.forms import ConfigIngredientForm



admin.site.register(models.Build)
admin.site.register(models.BuildPack)
admin.site.register(models.Host)
admin.site.register(models.DeploymentLogEntry)
admin.site.register(models.Swarm)

# Unregister the Django 'group' model, as I don't think we'll be using it.
admin.site.unregister(Group)


class ConfigIngredientAdmin(reversion.VersionAdmin):
    search_fields = ['name', 'value']
    ordering = ['name', ]
    list_display = ('name', 'used_in')
    form = ConfigIngredientForm

    def used_in(self, obj):
        if obj.swarm_set.all().count():
            return ", ".join([s.__unicode__()
                             for s in obj.swarm_set.all()])
        return "No Swarms"
    used_in.short_description = 'Included in'
admin.site.register(models.ConfigIngredient, ConfigIngredientAdmin)

# Recipes are dead, but the admin showed some nice stuff for them that should
# be moved to swarms.
#class ConfigRecipeAdmin(reversion.VersionAdmin):
    #inlines = [RecipeIngredientInline, ]
    #search_fields = ['name', 'ingredients__label', 'ingredients__value']
    #ordering = ['app__name', 'name']
    #list_display = ('__unicode__', 'show_ingredients', 'used_in')

    #def show_ingredients(self, obj):
        #if obj.ingredients.all().count():
            #return ", ".join([ing.label
                             #for ing in obj.ingredients.all()])
        #return "No Ingredients"
    #show_ingredients.short_description = "Ingredients"

    #def used_in(self, obj):
        #swarms = obj.swarm_set.all()
        #if swarms.count():
            #return ", ".join([swarm.shortname() for swarm in swarms])
        #return "No Swarms"
    #used_in.short_description = "Used in"


class HostInline(admin.TabularInline):
    model = models.Host


class SquadAdmin(admin.ModelAdmin):
    inlines = [HostInline]
admin.site.register(models.Squad, SquadAdmin)


class AppAdmin(admin.ModelAdmin):
    model = models.App
    list_display = ('__unicode__', 'repo_url')
admin.site.register(models.App, AppAdmin)


class TestResultInline(admin.TabularInline):
    model = models.TestResult
    extra = 0


class TestRunAdmin(admin.ModelAdmin):
    model = models.TestRun
    inlines = [TestResultInline]
admin.site.register(models.TestRun, TestRunAdmin)


class ReleaseAdmin(admin.ModelAdmin):
    search_fields = ['config', 'build__app__name']
admin.site.register(models.Release, ReleaseAdmin)

