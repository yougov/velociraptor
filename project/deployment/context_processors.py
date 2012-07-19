from django.conf import settings

from deployment.models import Swarm


# For showing a list of all swarms in the nav
def raptor(request):
    return {
        'swarms': Swarm.objects.filter(active=True),
        # Don't show web log links if syslogging is enabled
        'log_links': not settings.PROC_SYSLOG,
    }
