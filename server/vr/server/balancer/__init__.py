from django.conf import settings


def import_class(path):
    try:
        module, dot, klass = path.rpartition('.')
        imported = __import__(module, globals(), locals(), [klass, ], -1)
        return getattr(imported, klass)
    except Exception, e:
        raise ImportError(e)


def get_balancer(name):
    config = settings.BALANCERS[name]
    cls = import_class(config['BACKEND'])
    return cls(config)


def add_nodes(balancer_name, pool_name, nodes):
    """
    Given the name of a pool, and a list of nodes, add the nodes to the pool.
    The pool will be created if necessary.
    """
    get_balancer(balancer_name).add_nodes(pool_name, nodes)


def delete_nodes(balancer_name, pool_name, nodes):
    """
    Given the name of a pool and a list of nodes, remove the nodes from the
    pool, if present.
    """
    get_balancer(balancer_name).delete_nodes(pool_name, nodes)


def get_nodes(balancer_name, pool_name):
    return get_balancer(balancer_name).get_nodes(pool_name)
