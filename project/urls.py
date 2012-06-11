from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import ListView
from django.contrib import admin

from deployment.models import DeploymentLogEntry

admin.autodiscover()

urlpatterns = patterns('',
    # Main UI routes
    url(r'^$', 'deployment.views.dash', name='dash'),
    url(r'^swarm/$',
        'deployment.views.edit_swarm', name='new_swarm'),
    url(r'^swarm/(?P<swarm_id>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.edit_swarm', name='edit_swarm'),
    url(r'^deploy/$', 'deployment.views.deploy', name='deploy'),
    url(r'^build/$', 'deployment.views.build_hg', name='build_hg'),
    url(r'^release/$', 'deployment.views.release', name='release'),
    url(r'^upload/$', 'deployment.views.upload_build', name='upload_build'),
    url(r'^log/$', ListView.as_view(model=DeploymentLogEntry,
                                    template_name='log.html'), name='log'),

    # Utility stuff
    url(r'^login/$', 'deployment.views.login', name='login'),
    url(r'^logout/$', 'deployment.views.logout', name='logout'),
    url(r'^admin/', include(admin.site.urls)),

    # JSON API routes
    url(r'^api/hosts/$',
        'deployment.views.api_host', name='api_host'),
    url(r'^api/hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/ports/$',
        'deployment.views.api_host_ports', name='api_host_ports'),
    url(r'^api/hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/procs/$',
        'deployment.views.api_host_status', name='api_host_procs'),
    url(r'^api/hosts/(?P<host>[a-zA-Z0-9_.-]+)/procs/(?P<proc>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.api_host_proc', name='api_host_proc'),
    url(r'^api/task/$', 'deployment.views.api_task_recent',
        name='api_task_recent'),
    url(r'^api/task/(?P<task_id>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.api_task_status', name='api_task'),
)

urlpatterns += staticfiles_urlpatterns()
