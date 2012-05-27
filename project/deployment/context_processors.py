from deployment.models import Swarm

# For showing a list of all swarms in the nav
def swarms(request):
    return {'swarms': Swarm.objects.filter(active=True)}
