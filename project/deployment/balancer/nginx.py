import os
import re
import subprocess
import logging
import tempfile

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


class tmpfile(object):
    def __enter__(self):
        self.file = tempfile.mkstemp()
        return os.fdopen(self.file[0], 'w'), self.file[1]
    def __exit__(self, type, value, traceback):
        os.remove(self.file[1])


class LocalNginxBalancer(object):
    """
    A Velociraptor balancer backend for writing local nginx config.  Should be
    run as a user who doesn't need to enter a password for 'sudo'.  Not
    suitable for high availability environments, since it only supports a
    single nginx instance.
    """

    # User running Velociraptor must have write permissions on the include_dir.
    def __init__(self, config=None):
        config = {} if config is None else config
        self.include_dir = config.get('include_dir',
                                      '/etc/nginx/sites-enabled/')
        self.reload_cmd = config.get('reload_cmd', 'sudo /etc/init.d/nginx '
                                     'reload')

    def _get_filename(self, pool):
        return os.path.join(self.include_dir, pool) + '.conf'

    def _write_pool(self, pool, nodes):
        filename = self._get_filename(pool)
        with tmpfile() as tmp:
            f, tmpname = tmp
            contents = pool_to_str(pool, list(nodes))
            print contents
            f.write(contents)
            f.close()
            cmd = 'sudo cp %s %s' % (tmpname, filename)
            subprocess.call(cmd.split())

    def add_nodes(self, pool, nodes):
        existing_nodes = set(self.get_nodes(pool))
        self._write_pool(pool, existing_nodes.union(nodes))
        # reload nginx config.  Requires sudo
        subprocess.call(self.reload_cmd.split())

    def get_nodes(self, pool):
        filename = self._get_filename(pool)
        cmd = 'sudo cat ' + filename
        try:
            upstring = subprocess.check_output(cmd.split())
            written_pool, nodes = str_to_pool(upstring)
            if pool != written_pool:
                logging.error('Pool file %s contains mismatched name %s' %
                              (filename, written_pool))
            return nodes
        except subprocess.CalledProcessError:
            # missing file
            return []

    def delete_nodes(self, pool, nodes):
        existing_nodes = set(self.get_nodes(pool))
        self._write_pool(pool, existing_nodes.difference(nodes))
        subprocess.call(self.reload_cmd.split())
