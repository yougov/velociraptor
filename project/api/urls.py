from django.conf.urls.defaults import patterns, url, include

from api.resources import v1

urlpatterns = patterns('api.views',

    # SSE streams
    url(r'^streams/events/', 'event_stream', name='api_events'),
    url(r'^streams/proc_changes/$', 'proc_event_stream', name='api_proc_events'),

    # API over Supervisor RPC info
    url(r'^v1/hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/procs/$', 'host_procs',
        name='api_host_procs'),
    url(r'^v1/hosts/(?P<hostname>[a-zA-Z0-9_.-]+)/procs/(?P<procname>[a-zA-Z0-9_.-]+)/$',
        'host_proc', name='api_host_proc'),

    # TASTYPIE DRIVEN API
    (r'^', include(v1.urls)),
)
