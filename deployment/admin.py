from django.contrib import admin
from django.contrib.auth.models import Group

from deployment import models

# Register admin interfaces for our models.  This will be read during the
# admin.autodiscover() call in the project's urls.py
admin.site.register(models.ConfigValue)

class ProfileAdmin(admin.ModelAdmin):
    filter_horizontal = ('configvalues',)

admin.site.register(models.Profile, ProfileAdmin)

#admin.site.register(models.App, AppAdmin)
admin.site.register(models.App)
admin.site.register(models.Build)
admin.site.register(models.Release)
admin.site.register(models.Host)
admin.site.register(models.DeploymentLogEntry)

# Also unregister the Django 'group' model, as I don't think we'll be using it.
admin.site.unregister(Group)
