from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import ListView
from django.contrib import admin

from deployment.models import DeploymentLogEntry

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'deployment.views.dash', name='dash'),
    url(r'^deploy/$', 'deployment.views.deploy', name='deploy'),
    url(r'^build/$', 'deployment.views.build_hg', name='build_hg'),
    url(r'^release/$', 'deployment.views.release', name='release'),
    url(r'^upload/$', 'deployment.views.upload_build', name='upload_build'),
    url(r'^log/$', ListView.as_view(model=DeploymentLogEntry,
                                    template_name='log.html'), name='log'),
    url(r'^api/host/$',
        'deployment.views.api_host', name='api_host'),
    url(r'^api/host/(?P<hostname>[a-zA-Z0-9_.-]+)/ports/$',
        'deployment.views.api_host_ports', name='api_host_ports'),
    url(r'^api/host/(?P<hostname>[a-zA-Z0-9_.-]+)/procs/$',
        'deployment.views.api_host_status', name='api_host_procs'),
    url(r'^api/host/(?P<host>[a-zA-Z0-9_.-]+)/procs/(?P<proc>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.api_proc_status', name='api_host_proc'),
    url(r'^api/task/active/$', 'deployment.views.api_task_active',
        name='api_task_list'),
    url(r'^api/task/(?P<task_id>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.api_task_status', name='api_task'),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
