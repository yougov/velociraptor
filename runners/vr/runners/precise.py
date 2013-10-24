"""
Start a proc inside a container with essential system folders bind-mounted in.
Supports Ubuntu 12.04 (Precise).
"""
import os
import pwd
import grp
import argparse
import hashlib
import shutil
import tarfile
import subprocess
import pkg_resources
import fcntl
import errno
import stat

import requests

import yaml

from vr.common.paths import (ProcData, get_container_path, get_container_name,
                             get_proc_path, get_build_path, get_buildfile_path,
                             BUILDS_ROOT)
from vr.common.utils import tmpdir, randchars


def main():
    commands = {
        'setup': setup,
        'run': run,
        'shell': shell,
        'uptest': uptest,
        'teardown': teardown,
        }

    parser = argparse.ArgumentParser()
    cmd_help = "One of: %s" % ', '.join(commands.keys())
    parser.add_argument('command', help=cmd_help)
    parser.add_argument('file', help="Path to proc.yaml file.")

    args = parser.parse_args()

    # We intentionally don't close the file.  We leave it open and grab a lock
    # to avoid race conditions.
    f = open(args.file, 'rwb')

    settings = ProcData(yaml.safe_load(f))

    try:
        cmd = commands[args.command]
        # Commands that have a lock=False attribute won't try to lock the
        # proc.yaml file.  'uptest' and 'shell' are in this category.
        if getattr(cmd, 'lock', True):
            lock_file_or_die(f)
        cmd(settings)
    except KeyError:
        raise SystemExit("Command must be one of: %s" %
                         ', '.join(commands.keys()))


def setup(settings):
    print "Setting up", get_container_name(settings)
    ensure_build(settings)
    make_proc_dirs(settings)
    write_proc_lxc(settings)
    write_settings_yaml(settings)
    write_proc_sh(settings)
    write_env_sh(settings)


def run(settings):
    print "Running", get_container_name(settings)
    args = get_lxc_args(settings)
    os.execve(which('lxc-start')[0], args, {})


def shell(settings):
    print "Running shell for", get_container_name(settings)
    args = get_lxc_args(settings, special_cmd='/bin/bash')
    os.execve(which('lxc-start')[0], args, {})
shell.lock = False


def uptest(settings):
    # copy the uptester into the container. ensure it's executable.
    src = pkg_resources.resource_filename('vr.runners', 'uptester/uptester')
    container_path = get_container_path(settings)
    dest = os.path.join(container_path, 'uptester')
    shutil.copy(src, dest)
    st = os.stat(dest)
    os.chmod(dest, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    proc_name = getattr(settings, 'proc_name', None)
    if proc_name:
        build_path = get_build_path(settings)
        uptests_path = os.path.join(build_path, 'uptests', proc_name)
        if os.path.isdir(uptests_path):
            # run an LXC container for the uptests.
            inside_path = os.path.join('/app/uptests', proc_name)
            cmd = '/uptester %s %s %s ' % (inside_path, '127.0.0.1',
                                           settings.port)
            args = get_lxc_args(settings, special_cmd=cmd)
            os.execve(which('lxc-start')[0], args, {})
        else:
            # There are no uptests for this proc.  Output an empty JSON list.
            print "[]"
uptest.lock = False


def teardown(settings):
    # Everything should have been put in the proc path, so delete that.
    # We don't delete the build.  That will have to be cleaned up by someone
    # else.
    shutil.rmtree(get_proc_path(settings))


def lock_file_or_die(f):
    # Die hard and fast if another process has already grabbed the lock for
    # this proc.yaml
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            raise SystemExit("ERROR: %s is locked by another process." %
                             f.name)
        raise


def get_lxc_args(settings, special_cmd=None):

    name = get_container_name(settings)
    if special_cmd:
        cmd = special_cmd
        # Container names must be unique, so to allow running a shell or
        # uptests next to the app container we have to add more stuff to the
        # name.
        name += '-shell' + randchars()
    else:
        cmd = get_cmd(settings)

    return [
        'lxc-start',
        '--name', name,
        '--rcfile', os.path.join(get_proc_path(settings), 'proc.lxc'),
        '--',
        'su',
        '--preserve-environment',
        '--shell', '/bin/bash',
        '-c', 'cd /app;source /env.sh; exec /proc.sh "%s"' % cmd,
        settings.user
    ]


def get_template(name):
    """
    Look for 'name' in the vr.runners.templates folder.  Return its contents.
    """
    path = pkg_resources.resource_filename('vr.runners', 'templates/' + name)
    with open(path, 'rb') as f:
        return f.read()


def make_proc_dirs(settings):
    print "Making directories"
    proc_path = get_proc_path(settings)
    container_path = get_container_path(settings)
    mkdir(proc_path)
    mkdir(container_path)

    # make tmp dir.  Set owner
    tmp_path = os.path.join(container_path, 'tmp')
    mkdir(tmp_path)
    user = pwd.getpwnam(settings.user)
    os.chown(tmp_path, user.pw_uid, user.pw_gid)

    # make mount points too
    mountpoints = ('app',
                   'bin',
                   'dev',
                   'etc',
                   'lib',
                   'lib64',
                   'opt',
                   'usr',
                   'proc',
                   'run',
                   'sys',
                   'dev/pts',)
    for path in mountpoints:
        mkdir(os.path.join(container_path, path))

    volumes = getattr(settings, 'volumes', [])
    for outside, inside in volumes:
        mkdir(os.path.join(container_path, inside.lstrip('/')))


def mkdir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def write_env_sh(settings):
    print "Writing env.sh"
    envsh_path = os.path.join(get_container_path(settings), 'env.sh')

    with open(envsh_path, 'wb') as f:
        def format_var(key, val):
            return 'export %s="%s"' % (key, val)
        e = settings.env
        env_str = '\n'.join(format_var(k, e[k]) for k in e) + '\n'
        f.write(env_str)


def write_proc_lxc(settings):
    print "Writing proc.lxc"

    proc_path = get_proc_path(settings)
    build_path = get_build_path(settings)
    container_path = get_container_path(settings)

    tmpl = get_template('precise.lxc')

    content = tmpl % {
        'proc_path': container_path,
        'build_path': build_path,
    }

    # append lines to bind-mount volumes.
    volumes = getattr(settings, 'volumes', [])
    volume_tmpl = "\nlxc.mount.entry = %s %s%s none bind 0 0"
    for outside, inside in volumes:
        content += volume_tmpl % (outside, container_path, inside)

    filepath = os.path.join(proc_path, 'proc.lxc')
    with open(filepath, 'wb') as f:
        f.write(content)


def write_settings_yaml(settings):
    print "Writing settings.yaml"
    path = os.path.join(get_container_path(settings), 'settings.yaml')
    with open(path, 'wb') as f:
        f.write(yaml.safe_dump(settings.settings, default_flow_style=False))


def write_proc_sh(settings):
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
        'port': settings.port,
    }
    sh_path = os.path.join(get_container_path(settings), 'proc.sh')
    rendered = get_template('proc.sh') % context
    with open(sh_path, 'wb') as f:
        f.write(rendered)
    st = os.stat(sh_path)
    os.chmod(sh_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def get_cmd(settings):
    """
    If settings contains 'cmd', return that.

    Otherwise, read the Procfile inside the build code, parse it (as yaml), and
    pull out the command for settings.proc_name.
    """
    if hasattr(settings, 'cmd'):
        return settings.cmd

    procfile_path = os.path.join(get_build_path(settings), 'Procfile')
    with open(procfile_path, 'rb') as f:
        procs = yaml.safe_load(f)
    return procs[settings.proc_name]


def ensure_build(settings):
    """
    Given a URL to a build file, ensure that it's been downloaded to
    the builds folder.
    """
    path = get_buildfile_path(settings)

    # Ensure that builds_root has been created.
    mkdir(BUILDS_ROOT)

    if os.path.exists(path) and url_etag(settings.build_url) == file_md5(path):
        print "Build already downloaded"
    else:
        download_build(settings.build_url, path)

    # Now untar.
    outfolder = get_build_path(settings)
    if not os.path.isdir(outfolder):
        untar(settings)


def file_md5(filename):
    """
    Given a path to a file, read it chunk-wise and feed each chunk into
    an MD5 file hash.  Avoids having to hold the whole file in memory.
    Should return identical results though.
    """
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(128*md5.block_size), b''):
             md5.update(chunk)
    return md5.hexdigest()


def url_etag(url):
    """
    Given a URL, do a HEAD request and check for an ETag.  Return it if
    found, otherwise return empty string.
    """
    resp = requests.head(url)
    return resp.headers.get('ETag', '')


def untar(settings):
    tarpath = get_buildfile_path(settings)
    print "Untarring", tarpath
    outfolder = get_build_path(settings)
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
        user = pwd.getpwnam(settings.user)
        group = grp.getgrnam(settings.group)
        for root, dirs, files in os.walk('contents'):
            for d in dirs:
                path = os.path.join(root, d)
                # chown nobody:admin
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


        # Use mv to atomically put the folder in place unless already present 
        subprocess.check_call(['mv', '-nT', 'contents', outfolder])


def download_build(url, path):
    with tmpdir() as here:
        print "Downloading %s" % url
        base = os.path.basename(path)
        with open(base, 'wb') as f:
            resp = requests.get(url, stream=True)
            shutil.copyfileobj(resp.raw, f)
        shutil.move(base, path)


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


if __name__ == '__main__':
    main()
