from collections import defaultdict
import logging

from . import base

class DummyBalancer(base.Balancer):
    """
    Fake balancer class for local development.
    """
    def __init__(self, config):
        self.config = config
        self.pools = defaultdict(set)

    def add_nodes(self, pool, nodes):
        self.pools[pool].update(nodes)
        self.log_pool(pool)

    def delete_nodes(self, pool, nodes):
        self.pools[pool].difference_update(nodes)
        self.log_pool(pool)

    def get_nodes(self, pool):
        return self.pools[pool]

    def log_pool(self, pool):
        msg = 'Dummy Pool "%s": %s' % (pool, list(self.pools[pool]))
        logging.info(msg)
