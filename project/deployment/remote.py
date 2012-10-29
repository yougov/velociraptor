"""
Utilities for running commands and reading/writing files on remote hosts over
SSH.
"""

import os
import re
import sys
import traceback
import tempfile
import shutil
import hashlib
import pkg_resources
import paramiko
import random
import string
import posixpath

from fabric.api import run, sudo, get, put, task, env
from fabric.contrib import files
from fabric import colors
from fabric.context_managers import settings

# TODO: make these passed in so we can have a separate library of deployment
# tools that's free of YouGov-isms
PROCS_ROOT = '/opt/yg/procs'
RELEASES_ROOT = '/opt/yg/releases'


@task
def upload_release(build_path, config_path, release_path, user='nobody'):

    remote_procfile = posixpath.join(release_path, 'Procfile')

    if files.exists(remote_procfile):
        colors.green('%s already on server.  No need to upload.' % remote_procfile)
        return

    colors.green('Creating remote directory')
    sudo('mkdir -p ' + release_path)

    colors.green('Uploading build')
    #build_file = os.path.basename(build_path)
    # Make a random filename for the remote tmp file.
    rname = ''.join(random.choice(string.ascii_letters) for x in xrange(20))
    remote_build_path = posixpath.join('/tmp', rname)
    put(build_path, remote_build_path, use_sudo=True)

    colors.green('Unpacking build')

    tar_cmd = 'tar xjf {remote_build_path} -C {release_path} --strip-components 1'
    sudo(tar_cmd.format(**vars()))
    sudo('chown -R {user} {release_path}'.format(**vars()))
    sudo('chgrp -R admin {release_path}'.format(**vars()))
    sudo('chmod -R g+w {release_path}'.format(**vars()))
    # todo: mark directories as g+s

    colors.green('Uploading config')
    # If we let Fabric upload settings.yaml, it might step on its own toes when
    # there are simultaneous deployments.  So handle that ourselves.
    with SSHConnection(env.host_string, env.user, env.password) as ssh:
        ssh.put_file(config_path, posixpath.join(release_path,
                                                 'settings.yaml'), owner=user)

    colors.green('Deleting build tarball')
    sudo('rm ' + remote_build_path)


class chdir(object):
    def __init__(self, folder):
        self.orig_path = os.getcwd()
        self.temp_path = folder
    def __enter__(self):
        os.chdir(self.temp_path)
    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)


def parse_procfile(path):
    """
    Read a Procfile and return a dictionary with the proc names as keys and
    program locations as values.
    """
    with open(path, 'rb') as f:
        procs = dict([w.strip() for w in s.split(":", 1)] for s in f)
    return procs


def _quotevar(val):
    """Given a string, check whether it contains any non-alphanumeric chars,
    and wrap in quotes if so.  Else return the original.
    """
    if any((not c.isdigit() and not c.isalpha()) for c in val):
        return '"%s"' % val
    return val


def _env_to_str(env_dict):
    """Given a dictionary, return a string formatted appropriately for
    supervisord's 'env' config.  Non-alphanumeric values will be placed in
    quotes.
    """
    return ",".join("%s=%s" % (k, _quotevar(v)) for k, v in env_dict.items())


def _expand_env_vars(cmd, env_vars):
    """Given a command string and a dictionary of environment variables, look
    for any environment variables (like $PORT), and replace them with values
    from the dict if possible.
    """
    # If the var is in the dict, return the value from the dict.  Else return
    # the original var name.
    def sub(m):
        key = m.group(0)[1:]# strip off dollar sign
        if key in env_vars:
            return _quotevar(env_vars[key])
        return m.group(0)
    # env vars will be strings starting with a dollar sign followed by
    # continuous UPPERCASE, digits, and underscores.
    p = re.compile('\$[A-Z0-9_]+')
    return re.sub(p, sub, cmd)


def _create_proc_path(proc_path):
    # Create remote proc directory
    sudo('mkdir -p ' + proc_path)


@task
def configure_proc(release_name, proc, port, user='nobody', use_syslog=False):

    # Define some paths for using below.
    # procs have names like gryphon-2.2.3-d5338b8a07-web-5678
    proc_name = '-'.join([release_name, proc, str(port)])
    proc_path = posixpath.join(PROCS_ROOT, proc_name)
    proc_tmp_path = posixpath.join(proc_path, 'tmp')
    release_path = posixpath.join(RELEASES_ROOT, release_name)
    fabfile_path = os.path.dirname(os.path.abspath(__file__))
    env_bin_path = '%(release_path)s/env/bin' % vars()

    _create_proc_path(proc_path)

    env_vars = {'APP_SETTINGS_YAML': "%(release_path)s/settings.yaml" % vars(),
                'PORT': str(port),
                'PATH': ':'.join([
                    env_bin_path,
                    '/usr/local/sbin',
                    '/usr/local/bin',
                    '/usr/sbin',
                    '/usr/bin',
                    '/sbin:/bin']),
                'TMPDIR': proc_tmp_path}
    env = _env_to_str(env_vars)

    # Make a temporary copy of the Procfile for parsing.  Fetch it from the
    # host so we don't even need to have a local copy of the build in order to
    # add a new deploy of an existing release.
    tempdir = tempfile.mkdtemp()
    local_procfile = posixpath.join(tempdir, 'Procfile')
    get(posixpath.join(release_path, 'Procfile'), local_procfile)

    procs = parse_procfile(local_procfile)
    if not proc in procs:
        proc_names = ', '.join(procs.keys())
        raise KeyError("{proc} not found in Procfile ({proc_names} defined)"
            .format(**vars()))
    cmd = _expand_env_vars(procs[proc], env_vars)
    tmpl = pkg_resources.resource_filename('yg.deploy', 'fabric/proc.conf')
    remote_supd = posixpath.join(proc_path, 'proc.conf')

    # XXX Note that using 'syslog' here breaks supervisord's ability to show
    # the logs through its web and cmd line interfaces.  We should fix
    # supervisord so syslog can live alongside file logs rather than displacing
    # them.
    if use_syslog:
        stdout_log = stderr_log = "syslog"
    else:
        stdout_log = posixpath.join(proc_path, 'stdout.log')
        stderr_log = posixpath.join(proc_path, 'stderr.log')
    files.upload_template(tmpl, remote_supd, vars(), use_sudo=True)

    # write start_proc.sh from template
    sh_script = pkg_resources.resource_filename('yg.deploy',
                                                'fabric/start_proc.sh')
    sh_remote = posixpath.join(proc_path, 'start_proc.sh')
    sh_vars = dict(**env_vars)
    sh_vars.update(vars())
    files.upload_template(sh_script, sh_remote, sh_vars, use_sudo=True)
    sudo('chmod +x %s' % sh_remote)

    # Create a place for the proc to stick temporary files if it needs to.
    sudo('mkdir -p ' + proc_tmp_path)
    sudo('chown %(user)s %(proc_tmp_path)s' % vars())

    # Clean up our tempdir
    shutil.rmtree(tempdir)

    # For this to work, the host must have /opt/yg/procs/*/proc.conf in
    # the files include line in the main supervisord.conf
    sudo('supervisorctl reread')
    sudo('supervisorctl add ' + proc_name)


@task
def deploy_parcel(build_path, config_path, profile, proc, port, user='nobody',
                  checksum=None, use_syslog=False):
    # Builds have timstamps, but releases really don't care about them.  Two
    # releases created at different times with the same build and settings
    # should be treated the same.  So throw away the timestamp portion of the
    # build name when creating the release name.
    build_file = os.path.basename(build_path)
    nameparts = build_file.split('-')
    app_name = nameparts[0]
    version = nameparts[1]

    # A release name should look like gryphon-2.2.3-ldc-d5338b8a07, where the
    # random looking chars at the end come from a hash of the build tarball and
    # settings.yaml used for the release.
    chars = open(build_path, 'rb').read() + open(config_path, 'rb').read()
    release_hash = hashlib.md5(chars).hexdigest()[:8]

    # If a checksum has been passed, compare it to the computed release hash.
    # If they're not equal, bail out.
    if checksum:
        assert checksum == release_hash, "checksum != release_hash"

    release_name = '-'.join([app_name, version, profile, release_hash])
    release_path = posixpath.join(RELEASES_ROOT, release_name)

    # Ensure that the proc path is written before the release is uploaded, to
    # prevent a race condition with the scooper.
    proc_name = '-'.join([release_name, proc, str(port)])
    proc_path = posixpath.join(PROCS_ROOT, proc_name)
    _create_proc_path(proc_path)

    upload_release(build_path, config_path, release_path)

    configure_proc(release_name, proc, port, user, use_syslog=use_syslog)


def parse_procname(proc):
    app, version, profile, release_hash, procname, port = proc.split('-')
    return vars()


@task
def run_uptests(proc):
    # SSH to host, find the release for the proc, and look for files in its
    # 'uptests/<procname>' folder.  Run each one, passing in the hostname and
    # port.

    # Note that while we're currently using the proc's own copy of the release
    # code, this is not guaranteed to be the case in the future. The uptests
    # could be executed on any host, though we'll guarantee that the
    # environment's bin folder will be first on the path.
    procdata = parse_procname(proc)
    procname = procdata['procname']
    release_path = (RELEASES_ROOT + '/%(app)s-%(version)s-%(profile)s-%(release_hash)s' %
                    procdata)
    tests_path = '%s/uptests/%s/' % (release_path, procname)
    try:
        if not files.exists(tests_path):
            return []
        else:
            # now look for all files in the uptests folder
            test_files = sudo('ls -1 ' + tests_path).split()
            results = []
            for filename in test_files:
                # Build up command, with env vars and command line arguments.
                # Should look like:
                # <ENV> test_script <host> <port>
                cmd = ' '.join([
                    'PATH="%s/env/bin:$PATH"' % release_path,
                    'APP_SETTINGS_YAML="%s/settings.yaml"' % release_path,
                    tests_path + filename,
                    env.host or env.host_string,
                    procdata['port']
                ])
                with settings(warn_only=True):
                    result = run(cmd)
                results.append({
                    'uptest': filename,
                    'output': str(result),
                    'return_code': result.return_code,
                    'passed': result.return_code == 0,
                })
            return results
    except (Exception, SystemExit):
        # Fabric will raise SystemExit if we don't supply the right password
        # and abort_on_prompts is True.  Here we catch any exception raised
        # during the uptests and pass it back in the same format as other test
        # results.
        exc_type, exc_value, exc_traceback = sys.exc_info()
        return [{
            'uptest': None,
            'output': repr(traceback.format_exception(exc_type, exc_value,
                                          exc_traceback)),
            'return_code': 1,
            'passed': False,
        }]


@task
def delete_proc(proc):
    if not proc:
        raise SystemExit("You must supply a proc name")
    # stop the proc
    sudo('supervisorctl stop %s' % proc)
    # remove the proc
    sudo('supervisorctl remove %s' % proc)
    # delete the proc dir
    sudo('rm -rf /opt/yg/procs/%s' % proc)


@task
def delete_release(release, cascade=False):
    procs = sudo('ls -1 /opt/yg/procs').split()

    # this folder name parsing depends on procs being named like
    # dm2-0.0.4-2e257bb8-web-9009, and releases being named like
    # dm2-0.0.4-2e257bb8

    releases_in_use = set(['%(app)s-%(version)s-%(profile)s-%(release_hash)s' %
                           parse_procname(p) for p in procs])

    # see if there are procs pointing to this release
    # if so, and cascade==True, then delete procs pointing to this release.
    # Else fail.
    if release in releases_in_use:
        if cascade:
            # delete all procs for this release
            procs_to_delete = [p for p in procs if p.startswith(release)]
            for proc in procs_to_delete:
                delete_proc(proc)
        else:
            # Hi Jason.  I wanted to use Fabric's 'red' function to make this
            # error message stand out, but when running through yg-fab the
            # message doesn't seem to show at all.
            raise SystemExit('NOT DELETING %s. Release is currently in use, '
                             'and cascade=False' % release)
    sudo('rm -rf /opt/yg/releases/%s' % release)

@task
def clean_releases(execute=True):
    """ Check on /opt/yg/releases/ for releases without /opt/yg/procs/
    in use so we can clean them up.

    You may choose not to execute the actual delete (to test for example), and
    if you choose to be verbose it will print out the releases it will delete.

    Finally if one of the directory doesn't exist we return raise a SystemExit.
    """
    if files.exists('/opt/yg/procs', use_sudo=True) and \
        files.exists('/opt/yg/releases', use_sudo=True):
        procs = sudo('ls -1 /opt/yg/procs').split()
        releases = sudo('ls -1 /opt/yg/releases').split()
        releases_in_use = set([
            '%(app)s-%(version)s-%(profile)s-%(release_hash)s' %
            parse_procname(p) for p in procs])
        deleted = []
        for release in releases:
            if release not in releases_in_use:
                deleted.append(release)
                if execute:
                    delete_release(release, False)
        colors.green("Cleaned up %i releases." % len(deleted))
    else:
        raise SystemExit("Either /opt/yg/procs or /opt/yg/releases directory "\
                         "doesn't exist")


class SSHConnection(object):
    """
    A context manager for creating a non-Fabric SSH connection with a username and
    password, then ensuring it gets cleaned up.

    You can also instantiate this object without using it as a context manager.
    If you do, it's up to you to call close() when you're done.
    """
    def __init__(self, host, user, password, tmpdir='/tmp'):
        self.host = host
        self.user = user
        self.password = password
        self.tmpdir = tmpdir
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.host, username=self.user, password=self.password)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.ssh.close()

    def sudo(self, cmd):
        stdin, stdout, stderr = self.ssh.exec_command('sudo ' + cmd)
        stdin.write(self.password + '\n')
        stdin.flush()
        return stdout.read(), stderr.read()

    def write_file(self, path, contents, mode=0644, owner=None,
                   group=None):
        sftp = self.ssh.open_sftp()

        # There's no way to sftp.write as sudo, so we write to a temporary
        # location and then mv the file into place.
        tmppath = posixpath.join(self.tmpdir,
                                 ''.join(random.choice(string.ascii_letters) for x
                                         in xrange(10)))
        f = sftp.open(tmppath, 'wb')
        f.write(contents)
        f.close()
        sftp.chmod(tmppath, mode)
        # run sudo cmd to copy file to production location, and set owner/perms
        self.sudo('mv %s %s' % (tmppath, path))

        if owner:
            self.sudo('chown %s %s' % (owner, path))

        if group:
            self.sudo('chgrp %s %s' % (group, path))

    def put_file(self, local_path, remote_path, *args, **kwargs):
        return self.write_file(remote_path, open(local_path, 'rb').read(),
                               *args, **kwargs)
