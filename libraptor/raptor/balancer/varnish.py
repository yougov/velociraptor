import errno
import posixpath
import re

from deployment.balancer.base import SshBasedBalancer

BACKEND_TPL = '{.backend={.host="%(host)s"; .port="%(port)s";}}'

DIRECTOR_TPL = """
// This pool was written by Velociraptor.  You probably shouldn't edit it.
director %(pool)s round-robin {
%(backends)s
}
"""


def _render_backend(node):
    host, port = node.split(':')
    return BACKEND_TPL % {
        'host': host,
        'port': port,
    }


def pool_to_str(pool, nodes):
    # Return an empty string if there are no nodes.  A content-less include
    # file is probably OK, but directives with no contents probably aren't.
    if not nodes:
        return ''

    return DIRECTOR_TPL % {
        'backends': '  ' + '\n  '.join(_render_backend(n) for n in nodes),
        'pool': pool
    }


def str_to_pool(pool_str):
    # parse out the hosts and ports
    hs_and_ps = re.findall('host="(.*?)"; .port="(.*?)"', pool_str,
                           re.MULTILINE)
    # hs_and_ps will look like [('a', '50'), ('b', '9000')]
    nodes = ['%s:%s' % pair for pair in hs_and_ps]
    pool = re.search('director (.*?) ', pool_str).group(1)
    return pool, nodes

# I think we're gonna have to have a master raptor-pools.vcl include file that
# includes each pool.  The alternative is to try to parse the whole file and
# reconstruct it, which sounds risky.

# There's a lot of stuff in the nginx balancer that we're going to want in the
# varnish one, for connecting to SSH.  That'll need to go into a base class or
# helper functions.


class VarnishBalancer(SshBasedBalancer):

    def __init__(self, config):
        self.include_dir = config.get('include_dir',
                                      '/etc/varnish/')
        self.reload_cmd = config.get('reload_cmd',
                                     '/etc/init.d/varnish reload')
        self.main_pool_file = config.get('main_pool_file', 'pools.vcl')
        self.pool_file_prefix = config.get('pool_file_prefix', 'pool-')
        super(VarnishBalancer, self).__init__(config)

    def _get_poolfile(self, pool):
        return posixpath.join(self.include_dir, self.pool_file_prefix + pool +
                              '.vcl')

    def _get_host_nodes(self, host, pool):
        # Return set of nodes currently configured in a given host and pool

        filename = self._get_poolfile(pool)
        try:
            contents = self._read_file(host, filename)
            poolname, nodes = str_to_pool(contents)
        except IOError as e:
            # It's OK if the file doesn't exist.  But other IOErrors should be
            # raised normally.
            if e.errno == errno.ENOENT:
                nodes = []
            else:
                raise
        return set(nodes)

    def _get_include_line(self, pool):
        return 'include "%s";' % self._get_poolfile(pool)

    def _set_host_nodes(self, host, pool, nodes):
        # Write the pool file
        filename = self._get_poolfile(pool)
        contents = pool_to_str(pool, nodes)
        self._write_file(host, filename, contents)

        # Also ensure that there's a root include file that includes the one we
        # just wrote.
        main_file = posixpath.join(self.include_dir, self.main_pool_file)
        try:
            main_contents = self._read_file(host, main_file)
        except IOError as e:
            if e.errno == errno.ENOENT:
                main_contents = ''
            else:
                raise
        include_line = self._get_include_line(pool)
        if not include_line in main_contents:
            self._write_file(host, main_file, main_contents + '\n' +
                             include_line)
