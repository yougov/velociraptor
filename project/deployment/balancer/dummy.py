class DummyBalancer(object):
    def __init__(self, config):
        self.config = config

    def add_nodes(self, pool, nodes):
        pass

    def delete_nodes(self, pool, nodes):
        pass
