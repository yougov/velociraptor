from django.conf import settings

from vr.server.models import Swarm, Squad


def raptor(request):
    return {
        # For showing a list of all swarms in the nav
        'swarms': Swarm.objects.filter(),
        'squads': Squad.objects.all(),
        # Don't show web log links if syslogging is enabled
        'log_links': not settings.PROC_SYSLOG,
        'site_title': getattr(settings, 'SITE_TITLE', 'Velociraptor'),
        'custom_css': getattr(settings, 'CUSTOM_CSS', None),
        'max_events': getattr(settings, 'EVENTS_BUFFER_LENGTH', 100),
    }
