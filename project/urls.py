from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import ListView
from django.contrib import admin

from deployment.models import DeploymentLogEntry
from deployment.feeds import DeploymentLogFeed

admin.autodiscover()

urlpatterns = patterns('',
    # Main UI routes
    url(r'^$', 'deployment.views.dash', name='dash'),
    url(r'^swarm/$',
        'deployment.views.edit_swarm', name='new_swarm'),
    url(r'^swarm/(?P<swarm_id>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.edit_swarm', name='edit_swarm'),
    url(r'^squad/$',
        'deployment.views.edit_squad', name='new_squad'),
    url(r'^squad/(?P<squad_id>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.edit_squad', name='edit_squad'),
    url(r'^deploy/$', 'deployment.views.deploy', name='deploy'),
    url(r'^build/$', 'deployment.views.build_app', name='build_app'),
    url(r'^release/$', 'deployment.views.release', name='release'),
    url(r'^upload/$', 'deployment.views.upload_build', name='upload_build'),
    url(r'^log/$', ListView.as_view(model=DeploymentLogEntry,
                                    template_name='log.html'), name='log'),
    url(r'^log/rss/$', DeploymentLogFeed(), name='log_rss'),
    url(r'^proclog/(?P<hostname>[a-zA-Z0-9_.-]+)/(?P<procname>[a-zA-Z0-9_.-]+)/$',
        'deployment.views.proclog', name='proclog'),

    # Preview for Recipes configs
    url(r'^preview_recipe/(?P<recipe_id>\d+)/$',
        'deployment.views.preview_recipe', name='preview_recipe'),
    url(r'^preview_recipe_addchange/$',
        'deployment.views.preview_recipe_addchange',
        name='preview_recipe_addchange'),
    url(r'^preview_ingredient/(?P<recipe_id>\d+)/(?P<ingredient_id>\d+)/$',
        'deployment.views.preview_ingredient', name='preview_ingredient'),

    # Latest tag helper
    url(r'^get_latest_tag/(?P<recipe_id>\d+)/$',
        'deployment.views.get_latest_tag', name='get_latest_tag'),

    # Utility stuff
    url(r'^login/$', 'deployment.views.login', name='login'),
    url(r'^logout/$', 'deployment.views.logout', name='logout'),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^api/', include('api.urls')),
)

urlpatterns += staticfiles_urlpatterns()
