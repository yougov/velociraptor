from django.conf.urls.defaults import patterns, url, include

from api.resources import v1

urlpatterns = patterns('api.views',

    # LEGACY handcrafted API
    url(r'^hosts/$', 'host', name='api_hosts'),
    url(r'^hosts/_all/$', 'all_hosts', name='api_all_hosts'),
    url(r'^hosts/_active/$', 'active_hosts', name='api_active_hosts'),
    url(r'^hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/procs/$', 'host_procs',
        name='api_host_procs'),
    url(r'^hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/ports/$', 'host_ports',
        name='api_host_ports'),
    url(r'^hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/procs/(?P<procname>[a-zA-Z0-9_.-]+)/$',
        'host_proc', name='api_host_proc'),

    url(r'^uptest/latest/$', 'uptest_latest', name='api_uptest_latest'),
    url(r'^uptest/(?P<run_id>\d+)/$', 'uptest_run', name='api_uptest_run'),

    # SSE streams
    url(r'^events/', 'event_stream', name='api_events'),
    url(r'^hosts/_changes/$', 'host_change_stream', name='api_host_changes'),


    # TASTYPIE DRIVEN API
    (r'^', include(v1.urls)),
)
