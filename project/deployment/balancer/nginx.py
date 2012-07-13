import errno
import logging
import posixpath
import random
import re
import string
import warnings

import ssh
from django.conf import settings


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


class NginxBalancer(object):
    """
    A Velociraptor balancer backend for writing nginx config on remote servers.
    Uses sftp and ssh for writing files and running reload cmds.
    """

    def __init__(self, config=None):
        config = {} if config is None else config
        self.include_dir = config.get('include_dir',
                                      '/etc/nginx/sites-enabled/')
        self.reload_cmd = config.get('reload_cmd', '/etc/init.d/nginx reload')
        self.user = config.get('user', settings.DEPLOY_USER)
        self.password = config.get('password', settings.DEPLOY_PASSWORD)
        self.hosts = config.get('hosts', ['localhost'])
        self.tmpdir = config.get('tmpdir', '/tmp')

    def _get_connection(self, host):
        con = ssh.SSHClient()
        con.set_missing_host_key_policy(ssh.AutoAddPolicy())
        con.connect(host, username=self.user, password=self.password)
        return con

    def _read_file(self, host, path):
        # create connection
        con = self._get_connection(host)
        # read file with SFTP
        sftp = con.open_sftp()
        f = sftp.open(path, 'rb')
        contents = f.read()
        # close connection
        f.close()
        con.close()
        # return file contents
        return contents

    def _sudo(self, con, cmd):
        stdin, stdout, stderr = con.exec_command('sudo ' + cmd)
        stdin.write(self.password + '\n')
        stdin.flush()
        logging.info(stdout.read())

    def _write_file(self, host, path, contents):
        con = self._get_connection(host)
        # read file with SFTP
        sftp = con.open_sftp()
        # write file to temporary location
        tmppath = posixpath.join(self.tmpdir,
                                 ''.join(random.choice(string.lowercase) for x
                                         in xrange(10)))
        f = sftp.open(tmppath, 'wb')
        f.write(contents)
        f.close()
        sftp.chmod(tmppath, 0644)
        # run sudo cmd to copy file to production location, and set owner/perms
        self._sudo(con, 'mv %s %s' % (tmppath, path))
        self._sudo(con, 'chown root %s' % path)
        # close SSH connection
        con.close()

    def _reload_config(self, host):
        # connect
        con = self._get_connection(host)
        # run sudo cmd to reload nginx
        self._sudo(con, '/etc/init.d/nginx reload')
        # disconnect
        con.close()

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

    def _delete_host_nodes(self, host, pool, nodes):
        current = self._get_host_nodes(host, pool)
        correct = current.difference(nodes)
        self._set_host_nodes(host, pool, list(correct))

    def get_nodes(self, pool):
        # Look at the config files of all the hosts.  Raise a warning about any
        # mismatched pools.
        nodes = None
        for host in self.hosts:
            host_nodes = self._get_host_nodes(host, pool)
            if nodes is None:
                nodes = host_nodes
            elif host_nodes != nodes:
                warnings.warn('Host %s has nodes %s for pool %s, but other '
                              'hosts have %s' % (host, pool,
                                                 str(list(host_nodes)),
                                                 str(list(nodes))))
                nodes = nodes.union(host_nodes)
        if nodes:
            return list(nodes)
        return []

    def add_nodes(self, pool, nodes):
        nodeset = set(self.get_nodes(pool)).union(nodes)
        for host in self.hosts:
            self._set_host_nodes(host, pool, list(nodeset))
            self._reload_config(host)

    def delete_nodes(self, pool, nodes):
        for host in self.hosts:
            self._delete_host_nodes(host, pool, nodes)
            self._reload_config(host)
