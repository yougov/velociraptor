from django.contrib import admin
from django.contrib.auth.models import Group

from deployment import models

# Register admin interfaces for our models.  This will be read during the
# admin.autodiscover() call in the project's urls.py
admin.site.register(models.ConfigValue)

class ProfileConfigInline(admin.TabularInline):
    model = models.ProfileConfig

class ProfileAdmin(admin.ModelAdmin):
    inlines = [ProfileConfigInline]

admin.site.register(models.Profile, ProfileAdmin)

admin.site.register(models.App)
admin.site.register(models.Build)
admin.site.register(models.Release)
admin.site.register(models.Host)
admin.site.register(models.DeploymentLogEntry)

# Also unregister the Django 'group' model, as I don't think we'll be using it.
admin.site.unregister(Group)
