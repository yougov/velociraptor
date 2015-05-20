import reversion

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User

from vr.server import models
from vr.server.forms import ConfigIngredientForm

admin.site.register(models.Build)
admin.site.register(models.BuildPack)
admin.site.register(models.DeploymentLogEntry)
admin.site.register(models.Host)
admin.site.register(models.OSImage)
admin.site.register(models.OSStack)

# Unregister the Django 'group' model, as I don't think we'll be using it.
admin.site.unregister(Group)


class ConfigIngredientAdmin(reversion.VersionAdmin):
    search_fields = ['name', 'env_yaml', 'config_yaml']
    ordering = ['name']
    list_display = ('name', 'used_in')
    form = ConfigIngredientForm

    def used_in(self, obj):
        if obj.swarm_set.all().count():
            return ", ".join([s.__unicode__() for s in obj.swarm_set.all().only(
                'release', 'config_name', 'proc_name')])
        return "No Swarms"
    used_in.short_description = 'Included in'
admin.site.register(models.ConfigIngredient, ConfigIngredientAdmin)


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
    search_fields = ['config_yaml', 'env_yaml', 'build__app__name']
    list_filter = ['build__app']
admin.site.register(models.Release, ReleaseAdmin)

admin.site.unregister(User)

class UserProfileInline(admin.StackedInline):
    model = models.UserProfile

class UserProfileAdmin(UserAdmin, reversion.VersionAdmin):
    """ User Admin override, add an inline.
    """
    inlines = [UserProfileInline]

admin.site.register(User, UserProfileAdmin)

class DashboardAdmin(admin.ModelAdmin):
    model = models.Dashboard

admin.site.register(models.Dashboard, DashboardAdmin)

class SwarmAdmin(admin.ModelAdmin):
    model = models.Swarm
    # Make release readonly, to avoid "N+1 query" issues
    # See https://bitbucket.org/yougov/velociraptor/issue/151/error-in-admin-swarm-pages
    readonly_fields = ('release', )

admin.site.register(models.Swarm, SwarmAdmin)
