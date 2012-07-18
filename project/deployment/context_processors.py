from deployment import models


# For showing a list of all swarms in the nav
def navdata(request):
    return {
        'swarms': models.Swarm.objects.filter(active=True),
        'squads': models.Squad.objects.all(),
        'recipes': models.ConfigRecipe.objects.all(),
    }
