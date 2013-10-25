import os
import stat
import fcntl
import errno
import pwd
import grp
import shutil
import hashlib
import tarfile
import pkg_resources
import argparse
import socket

import requests
import yaml

from vr.common.paths import (ProcData, get_container_name, get_buildfile_path,
                             BUILDS_ROOT, get_app_path, get_container_path,
                             get_proc_path)
from vr.common.utils import tmpdir, randchars

class BaseRunner(object):
    def main(self):
        self.commands = {
            'setup': self.setup,
            'run': self.run,
            'shell': self.shell,
            'uptest': self.uptest,
            'teardown': self.teardown,
        }

        parser = argparse.ArgumentParser()
        cmd_help = "One of: %s" % ', '.join(self.commands.keys())
        parser.add_argument('command', help=cmd_help)
        parser.add_argument('file', help="Path to proc.yaml file.")

        args = parser.parse_args()

        # We intentionally don't close the file.  We leave it open and grab a lock
        # to ensure that two runners aren't trying to run the same proc. 
        self.file = open(args.file, 'rwb')

        self.config = ProcData(yaml.safe_load(self.file))

        try:
            cmd = self.commands[args.command]
            # Commands that have a lock=False attribute won't try to lock the
            # proc.yaml file.  'uptest' and 'shell' are in this category.
            if getattr(cmd, 'lock', True):
                lock_file_or_die(self.file)
            else:
                self.file.close()
        except KeyError:
            raise SystemExit("Command must be one of: %s" %
                             ', '.join(self.commands.keys()))
        cmd()

    def setup(self):
        print "Setting up", get_container_name(self.config)
        self.make_proc_dirs()
        self.ensure_build()
        self.write_proc_lxc()
        self.write_settings_yaml()
        self.write_proc_sh()
        self.write_env_sh()

    def run(self):
        print "Running", get_container_name(self.config)
        args = self.get_lxc_args()
        os.execve(which('lxc-start')[0], args, {})

    def shell(self):
        print "Running shell for", get_container_name(self.config)
        args = self.get_lxc_args(special_cmd='/bin/bash')
        os.execve(which('lxc-start')[0], args, {})
    shell.lock = False

    def untar(self):
        tarpath = get_buildfile_path(self.config)
        print "Untarring", tarpath
        outfolder = get_app_path(self.config)
        # make a folder to untar to 
        with tmpdir() as here:
            _, _, ext = tarpath.rpartition('.')

            if ext not in ('gz', 'bz2'):
                raise ValueError('tarpath must point to a .gz or .bz2 file')

            tf = tarfile.open(tarpath, 'r:'+ext)
            try:
                os.mkdir('contents')
                tf.extractall('contents')
            finally:
                tf.close()

            # now fix all the perms
            user = pwd.getpwnam(self.config.user)
            group = grp.getgrnam(self.config.group)
            for root, dirs, files in os.walk('contents'):
                for d in dirs:
                    path = os.path.join(root, d)
                    # chown user:group
                    os.chown(path, user.pw_uid, group.gr_gid)
                    st = os.stat(path)
                    # chmod ug+xr 
                    os.chmod(path, st.st_mode | stat.S_IXUSR
                                              | stat.S_IXGRP
                                              | stat.S_IRUSR
                                              | stat.S_IRGRP)
                for f in files:
                    path = os.path.join(root, f)
                    if not os.path.islink(path):
                        # chown nobody:admin
                        os.chown(path, user.pw_uid, group.gr_gid)
                        st = os.stat(path)
                        # chmod ug+rw
                        os.chmod(path, st.st_mode | stat.S_IWUSR
                                                  | stat.S_IWGRP
                                                  | stat.S_IRUSR
                                                  | stat.S_IRGRP)

            # Each proc gets its own copy of the build.  If there's already one
            # there, assume that 'setup' has been called again to fix a screwed up
            # proc.  In that case, we should remove the build that's there and
            # replace it with the fresh copy.
            if os.path.isdir(outfolder):
                shutil.rmtree(outfolder)
            os.rename('contents', outfolder)

    def write_proc_sh(self):
        """
        Write the script that is the first thing called inside the container.  It
        sets env vars and then calls the real program.
        """
        print "Writing proc.sh"
        context = {
            'tmp': '/tmp',
            'home': '/app',
            'settings': '/settings.yaml',
            'envsh': '/env.sh',
            'port': self.config.port,
            'cmd': self.get_cmd(),
        }
        sh_path = os.path.join(get_container_path(self.config), 'proc.sh')
        rendered = get_template('proc.sh') % context
        with open(sh_path, 'wb') as f:
            f.write(rendered)
        st = os.stat(sh_path)
        os.chmod(sh_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def write_env_sh(self):
        print "Writing env.sh"
        envsh_path = os.path.join(get_container_path(self.config), 'env.sh')

        with open(envsh_path, 'wb') as f:
            def format_var(key, val):
                return 'export %s="%s"' % (key, val)
            e = self.config.env
            env_str = '\n'.join(format_var(k, e[k]) for k in e) + '\n'
            f.write(env_str)

    def get_cmd(self):
        """
        If self.config contains 'cmd', return that.

        Otherwise, read the Procfile inside the build code, parse it (as yaml), and
        pull out the command for self.config.proc_name.
        """
        if hasattr(self.config, 'cmd'):
            return self.config.cmd

        procfile_path = os.path.join(get_app_path(self.config), 'Procfile')
        with open(procfile_path, 'rb') as f:
            procs = yaml.safe_load(f)
        return procs[self.config.proc_name]

    def ensure_build(self):
        """
        Given a URL to a build file, ensure that it's been downloaded to
        the builds folder.
        """
        path = get_buildfile_path(self.config)

        # Ensure that builds_root has been created.
        mkdir(BUILDS_ROOT)

        if os.path.exists(path) and url_etag(self.config.build_url) == file_md5(path):
            print "Build already downloaded"
        else:
            download_build(self.config.build_url, path)

        # Now untar.
        outfolder = get_app_path(self.config)
        self.untar()

    def write_settings_yaml(self):
        print "Writing settings.yaml"
        path = os.path.join(get_container_path(self.config), 'settings.yaml')
        with open(path, 'wb') as f:
            f.write(yaml.safe_dump(self.config.settings, default_flow_style=False))

    def get_lxc_args(self, special_cmd=None):

        name = get_container_name(self.config)
        if special_cmd:
            cmd = special_cmd
            # Container names must be unique, so to allow running a shell or
            # uptests next to the app container we have to add more stuff to the
            # name.
            name += '-tmp' + randchars()
        else:
            cmd = 'run'

        return [
            'lxc-start',
            '--name', name,
            '--rcfile', os.path.join(get_proc_path(self.config), 'proc.lxc'),
            '--',
            'su',
            '--preserve-environment',
            '--shell', '/bin/bash',
            '-c', 'cd /app;source /env.sh; exec /proc.sh "%s"' % cmd,
            self.config.user
        ]

    def get_lxc_volume_str(self):
        content = ''
        # append lines to bind-mount volumes.
        volumes = getattr(self.config, 'volumes', [])
        volume_tmpl = "\nlxc.mount.entry = %s %s%s none bind 0 0"
        for outside, inside in volumes:
            content += volume_tmpl % (outside, container_path, inside)
        return content

    def uptest(self):
        # copy the uptester into the container. ensure it's executable.
        src = pkg_resources.resource_filename('vr.runners', 'uptester/uptester')
        container_path = get_container_path(self.config)
        dest = os.path.join(container_path, 'uptester')
        shutil.copy(src, dest)
        st = os.stat(dest)
        os.chmod(dest, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        proc_name = getattr(self.config, 'proc_name', None)
        if proc_name:
            app_path = get_app_path(self.config)
            uptests_path = os.path.join(app_path, 'uptests', proc_name)
            if os.path.isdir(uptests_path):
                # run an LXC container for the uptests.
                inside_path = os.path.join('/app/uptests', proc_name)
                cmd = '/uptester %s %s %s ' % (inside_path, socket.getfqdn(),
                                               self.config.port)
                args = self.get_lxc_args(special_cmd=cmd)
                os.execve(which('lxc-start')[0], args, {})
            else:
                # There are no uptests for this proc.  Output an empty JSON list.
                print "[]"
    uptest.lock = False

    def teardown(self):
        # Everything should have been put in the proc path, so delete that.
        # We don't delete the build.  That will have to be cleaned up by someone
        # else.
        shutil.rmtree(get_proc_path(self.config))

    def make_proc_dirs(self):
        raise NotImplementedError('Subclasses should implement this.')

    def write_proc_lxc(self):
        raise NotImplementedError('Subclasses should implement this.')


def download_build(url, path):
    with tmpdir() as here:
        print "Downloading %s" % url
        base = os.path.basename(path)
        with open(base, 'wb') as f:
            resp = requests.get(url, stream=True)
            shutil.copyfileobj(resp.raw, f)
        os.rename(base, path)


def url_etag(url):
    """
    Given a URL, do a HEAD request and check for an ETag.  Return it if
    found, otherwise return empty string.
    """
    resp = requests.head(url)
    return resp.headers.get('ETag', '')


def which(name, flags=os.X_OK):
    """
    Search PATH for executable files with the given name.

    Taken from Twisted.
    """
    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
    return result


def get_template(name):
    """
    Look for 'name' in the vr.runners.templates folder.  Return its contents.
    """
    path = pkg_resources.resource_filename('vr.runners', 'templates/' + name)
    with open(path, 'rb') as f:
        return f.read()


def mkdir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def file_md5(filename):
    """
    Given a path to a file, read it chunk-wise and feed each chunk into
    an MD5 file hash.  Avoids having to hold the whole file in memory.
    """
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(128*md5.block_size), b''):
             md5.update(chunk)
    return md5.hexdigest()


def lock_file_or_die(f):
    """
    Die hard and fast if another process has already grabbed the lock for
    this proc.yaml
    """
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            raise SystemExit("ERROR: %s is locked by another process." %
                             f.name)
        raise
