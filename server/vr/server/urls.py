from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin

from vr.server import views
from vr.server.feeds import DeploymentLogFeed

admin.autodiscover()

urlpatterns = patterns('',
    # Main UI routes
    url(r'^$', 'vr.server.views.dash', name='dash'),
    url(r'^swarm/$',
        'vr.server.views.edit_swarm', name='new_swarm'),
    url(r'^swarm/(?P<swarm_id>[a-zA-Z0-9_.-]+)/$',
        'vr.server.views.edit_swarm', name='edit_swarm'),
    url(r'^deploy/$', 'vr.server.views.deploy', name='deploy'),
    url(r'^build/$', 'vr.server.views.build_app', name='build_app'),
    url(r'^release/$', 'vr.server.views.release', name='release'),
    url(r'^upload/$', 'vr.server.views.upload_build', name='upload_build'),
    url(r'^log/$', views.ListLogEntry.as_view(), name='log'),
    url(r'^log/rss/$', DeploymentLogFeed(), name='log_rss'),
    url(r'^proclog/(?P<hostname>[a-zA-Z0-9_.-]+)/(?P<procname>[a-zA-Z0-9_.-]+)/$',
        'vr.server.views.proclog', name='proclog'),

    # Utility stuff
    url(r'^login/$', 'vr.server.views.login', name='login'),
    url(r'^logout/$', 'vr.server.views.logout', name='logout'),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^files/(?P<path>.+)', 'vr.server.storages.serve_file', name='serve_file'),

    url(r'^api/', include('api.urls')),

    # Ingredient CRUD
    url(r'^ingredient/$', login_required(views.ListConfigIngredient.as_view()),
        name='ingredient_list'),
    url(r'^ingredient/add/$',login_required(
        views.AddConfigIngredient.as_view()),
        name='ingredient_add'),
    url(r'^ingredient/(?P<pk>\d+)/$',
        login_required(views.UpdateConfigIngredient.as_view()),
        name='ingredient_update'),
    url(r'^ingredient/(?P<pk>\d+)/delete/$',
        login_required(views.DeleteConfigIngredient.as_view()),
        name='ingredient_delete'),

    # Host CRUD
    url(r'^host/$', login_required(views.ListHost.as_view()),
        name='host_list'),
    url(r'^host/add/$', login_required(views.AddHost.as_view()),
        name='host_add'),
    url(r'^host/(?P<pk>\d+)/$', login_required(views.UpdateHost.as_view()),
        name='host_update'),
    url(r'^host/(?P<pk>\d+)/delete/$',
        login_required(views.DeleteHost.as_view()),
        name='host_delete'),

    # Squad CRUD
    url(r'^squad/$', login_required(views.ListSquad.as_view()),
        name='squad_list'),
    url(r'^squad/add/$', login_required(views.AddSquad.as_view()),
        name='squad_add'),
    url(r'^squad/(?P<pk>\d+)/$', login_required(views.UpdateSquad.as_view()),
        name='squad_update'),
    url(r'^squad/(?P<pk>\d+)/delete/$',
        login_required(views.DeleteSquad.as_view()),
        name='squad_delete'),

    # App CRUD
    url(r'^app/$', login_required(views.ListApp.as_view()),
        name='app_list'),
    url(r'^app/add/$', login_required(views.AddApp.as_view()),
        name='app_add'),
    url(r'^app/(?P<pk>\d+)/$', login_required(views.UpdateApp.as_view()),
        name='app_update'),
    url(r'^app/(?P<pk>\d+)/delete/$', login_required(views.DeleteApp.as_view()),
        name='app_delete'),

    # BuildPack CRUD
    url(r'^buildpack/$', login_required(views.ListBuildPack.as_view()),
        name='buildpack_list'),
    url(r'^buildpack/add/$', login_required(views.AddBuildPack.as_view()),
        name='buildpack_add'),
    url(r'^buildpack/(?P<pk>\d+)/$',
        login_required(views.UpdateBuildPack.as_view()),
        name='buildpack_update'),
    url(r'^buildpack/(?P<pk>\d+)/delete/$',
        login_required(views.DeleteBuildPack.as_view()),
        name='buildpack_delete'),
)

urlpatterns += staticfiles_urlpatterns()
