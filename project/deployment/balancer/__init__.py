from django.conf import settings


def import_class(path):
    try:
        module, dot, klass = path.rpartition('.')
        imported = __import__(module, globals(), locals(), [klass, ], -1)
        return getattr(imported, klass)
    except Exception, e:
        raise ImportError(e)

# Only instantiate the balancer on first import
if not 'balancers' in globals():
    # loop over settings.BALANCERS, instantiate a balancer for each, and put it
    # in the 'balancers' dict in this module.
    balancers = {}
    for name, config in settings.BALANCERS.items():
        balancers[name] = import_class(config['BACKEND'])(config)

def add_nodes(pool_name, nodes, balancer='default'):
    """
    Given the name of a pool, and a list of nodes, add the nodes to the pool.
    The pool will be created if necessary.
    """
    balancers[balancer].add_nodes(pool_name, nodes)

def delete_nodes(pool_name, nodes, balancer='default'):
    """
    Given the name of a pool and a list of nodes, remove the nodes from the
    pool, if present.
    """
    balancers[balancer].delete_nodes(pool_name, nodes)

def get_nodes(pool_name, balancer='default'):
    return balancers[balancer].get_nodes(pool_name)
