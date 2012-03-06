from django.contrib import admin
from django.contrib.auth.models import Group

from deployment.models import (DeploymentLogEntry, App, Build, Release,
                               Deployment)

# Register admin interfaces for our models.  This will be read during the
# admin.autodiscover() call in the project's urls.py
admin.site.register(App)
admin.site.register(Build)
admin.site.register(Release)
admin.site.register(Deployment)
admin.site.register(DeploymentLogEntry)

# Also unregister the Django 'group' model, as I don't think we'll be using it.
admin.site.unregister(Group)
