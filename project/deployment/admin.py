import reversion

from django.contrib import admin
from django.contrib.auth.models import Group

from deployment import models
from deployment.forms import ConfigIngredientForm


class RecipeIngredientInline(admin.TabularInline):
    model = models.RecipeIngredient


class ConfigIngredientAdmin(reversion.VersionAdmin):
    search_fields = ['label', 'value']
    ordering = ['label', ]
    list_display = ('label', 'used_in')
    form = ConfigIngredientForm

    def used_in(self, obj):
        if obj.configrecipe_set.all().count():
            return ", ".join([recipe.__unicode__()
                             for recipe in obj.configrecipe_set.all()])
        return "No recipes"
    used_in.short_description = 'Included in'


class ConfigRecipeAdmin(reversion.VersionAdmin):
    inlines = [RecipeIngredientInline, ]
    search_fields = ['name', 'ingredients__label', 'ingredients__value']
    ordering = ['app__name', 'name']
    list_display = ('__unicode__', 'show_ingredients', 'used_in')

    def show_ingredients(self, obj):
        if obj.ingredients.all().count():
            return ", ".join([ing.label
                             for ing in obj.ingredients.all()])
        return "No Ingredients"
    show_ingredients.short_description = "Ingredients"

    def used_in(self, obj):
        swarms = obj.swarm_set.all()
        if swarms.count():
            return ", ".join([swarm.shortname() for swarm in swarms])
        return "No Swarms"
    used_in.short_description = "Used in"


class HostInline(admin.TabularInline):
    model = models.Host


class SquadAdmin(admin.ModelAdmin):
    inlines = [HostInline]


class AppAdmin(admin.ModelAdmin):
    model = models.App
    list_display = ('__unicode__', 'repo_url')


class TestResultInline(admin.TabularInline):
    model = models.TestResult
    extra = 0


class TestRunAdmin(admin.ModelAdmin):
    model = models.TestRun
    inlines = [TestResultInline]


class ReleaseAdmin(admin.ModelAdmin):
    search_fields = ['config', 'recipe__app__name']


admin.site.register(models.ConfigRecipe, ConfigRecipeAdmin)
admin.site.register(models.Squad, SquadAdmin)
admin.site.register(models.ConfigIngredient, ConfigIngredientAdmin)
admin.site.register(models.App, AppAdmin)
admin.site.register(models.Build)
admin.site.register(models.Release, ReleaseAdmin)
admin.site.register(models.Host)
admin.site.register(models.DeploymentLogEntry)
admin.site.register(models.Swarm)
admin.site.register(models.TestRun, TestRunAdmin)


# Unregister the Django 'group' model, as I don't think we'll be using it.
admin.site.unregister(Group)

# Unregister the djcelery models.
#import djcelery.models
#admin.site.unregister(djcelery.models.TaskState)
#admin.site.unregister(djcelery.models.WorkerState)
#admin.site.unregister(djcelery.models.IntervalSchedule)
#admin.site.unregister(djcelery.models.CrontabSchedule)
#admin.site.unregister(djcelery.models.PeriodicTask)
