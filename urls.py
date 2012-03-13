from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import ListView
from django.contrib import admin

from deployment.models import DeploymentLogEntry

# Tell the Django admin to scan all apps in our project and automatically
# display their admin interfaces.
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'deployment.views.dash', name='dash'),
    url(r'^deploy/$', 'deployment.views.deploy', name='deploy'),
    url(r'^log/$', ListView.as_view(model=DeploymentLogEntry,
                                    template_name='log.html'), name='log'),
    url(r'^api/status/(?P<host>[a-zA-Z0-9_.]+)/$', 'deployment.views.api_host_status',
        name='api_host_status'),
    url(r'^api/status/(?P<host>[a-zA-Z0-9_.]+)/(?P<proc>[a-zA-Z0-9_.]+)/$', 'deployment.views.api_proc_status',
        name='api_proc_status'),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
