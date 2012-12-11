import errno
import posixpath
import re

from . import base

# Template for 'upstream' directive in nginx config.
UPSTREAM_TPL = """
upstream %(name)s {
%(lines)s
}
"""


def pool_to_str(name, nodes):
    """
    Given a list of nodes, return a string containing a properly-formatted
    'upstream' section for nginx config.
    """
    return UPSTREAM_TPL % {
        'name': name,
        'lines': '\n'.join(['  server %s;' % n for n in nodes])
    }


def str_to_pool(upstream):
    """
    Given a string containing an nginx upstream section, return the pool name
    and list of nodes.
    """
    name = re.search('upstream +(.*?) +{', upstream).group(1)
    nodes = re.findall('server +(.*?);', upstream)
    return name, nodes


class NginxBalancer(base.SshBasedBalancer):
    """
    A Velociraptor balancer backend for writing nginx config on remote servers.
    Uses sftp and ssh for writing files and running reload cmds.
    """

    def __init__(self, config):
        self.include_dir = config.get('include_dir',
                                      '/etc/nginx/sites-enabled/')
        self.reload_cmd = config.get('reload_cmd', '/etc/init.d/nginx reload')
        super(NginxBalancer, self).__init__(config)

    def _get_host_nodes(self, host, pool):
        # Return set of nodes currently configured in a given host and pool

        path = posixpath.join(self.include_dir, pool + '.conf')
        try:
            contents = self._read_file(host, path)
            poolname, nodes = str_to_pool(contents)
        except IOError as e:
            # It's OK if the file doesn't exist.  But other IOErrors should be
            # raised normally.
            if e.errno == errno.ENOENT:
                nodes = []
            else:
                raise
        return set(nodes)

    def _set_host_nodes(self, host, pool, nodes):
        path = posixpath.join(self.include_dir, pool + '.conf')
        contents = pool_to_str(pool, nodes)
        self._write_file(host, path, contents)
