"""
Utilities for running commands and reading/writing files on remote hosts over
SSH.
"""

import os
import traceback
import tempfile
import shutil
import hashlib
import paramiko
import random
import string
import posixpath
import pkg_resources
import json
import re

from fabric.api import sudo, get, put, task, env
from fabric.contrib import files
from fabric import colors

from raptor.models import Proc

BUILDS_ROOT = '/apps/builds'
PROCS_ROOT = '/apps/procs'
RELEASES_ROOT = '/apps/releases'


@task
def upload_build(local_path, build_name, user='nobody'):

    remote_path = posixpath.join(BUILDS_ROOT, build_name)
    if not files.exists(remote_path):
        sudo('mkdir -p ' + remote_path)
    remote_procfile = posixpath.join(remote_path, 'Procfile')

    if files.exists(remote_procfile):
        colors.green('%s already on server.  No need to upload.' % remote_procfile)
        return


    # check if the build is needed.  upload if so.

    colors.green('Uploading build')
    # Make a random filename for the remote tmp file.
    tmp_path = posixpath.join('/tmp',
                              ''.join(random.choice(string.ascii_letters) for x
                                      in xrange(20)))
    put(local_path, tmp_path, use_sudo=True)

    colors.green('Unpacking build')

    tar_cmd = 'tar xjf {tmp_path} -C {remote_path} --strip-components 1'
    tar_cmd = tar_cmd.format(**vars())
    sudo(tar_cmd)
    sudo('chown -R {user} {remote_path}'.format(**vars()))
    sudo('chgrp -R admin {remote_path}'.format(**vars()))
    sudo('chmod -R g+w {remote_path}'.format(**vars()))
    # todo: mark directories as g+s

    colors.green('Deleting build tarball')
    sudo('rm ' + tmp_path)


@task
def upload_release(build_path, build_name, config_path, release_path, envsh_path, user='nobody'):
    # See if /apps/releases/<name> exists.  If not, make it.
    if not files.exists(release_path):
        colors.green('Creating remote directory')
        sudo('mkdir -p ' + release_path)

    upload_build(build_path, build_name)

    colors.green('Uploading config')
    # If we let Fabric upload settings.yaml, it might step on its own toes when
    # there are simultaneous deployments.  So handle that ourselves.
    with SSHConnection(env.host_string, env.user, env.password) as ssh:
        ssh.put_file(config_path, posixpath.join(release_path,
                                                 'settings.yaml'), owner=user)
        ssh.put_file(envsh_path, posixpath.join(release_path, 'env.sh'),
                     owner=user)


def parse_procfile(path):
    """
    Read a Procfile and return a dictionary with the proc names as keys and
    program locations as values.
    """
    with open(path, 'rb') as f:
        procs = dict([w.strip() for w in s.split(":", 1)] for s in f)
    return procs


def get_template(name):
    here = os.path.dirname(__file__)
    return os.path.join(here, 'templates', name)


class Deployer(object):
    mountpoints = []
    lxc_config_template = None

    def __init__(self, build_name, release_name, proc, port, user, use_syslog):
        self.build_name = build_name
        self.release_name = release_name
        self.proc = proc
        self.port = port
        self.user = user
        self.use_syslog = use_syslog
        self.proc_name = '-'.join([release_name, proc, str(port)])
        self.proc_path = posixpath.join(PROCS_ROOT, self.proc_name)
        self.proc_tmp_path = posixpath.join(self.proc_path, 'tmp')
        self.build_path = posixpath.join(BUILDS_ROOT, self.build_name)
        self.release_path = posixpath.join(RELEASES_ROOT, self.release_name)

        self.envsh_path = posixpath.join(self.proc_path, 'env.sh')
        self.yaml_settings_path = posixpath.join(self.proc_path,
                                                 "settings.yaml")
        self.proc_line = self.get_proc_line()

    def run(self):
        """
        Do everything needed to get the proc running on the remote host.
        """
        self.configure_proc()
        self.reload_supervisor()

    def configure_proc(self):
        """
        Wrap all the functions needed to get a proc configured on the remote
        host.
        """
        sudo('mkdir -p ' + self.proc_path)

        self.write_proc_conf()
        self.write_proc_lxc()
        self.write_start_proc_sh()
        self.write_start_proc_inner()
        self.create_proc_tmpdir()
        self.upload_uptester()
        self.create_mount_points()
        self.copy_config()

    def copy_config(self):
        """
        On the remote host, copy settings.yaml and env.sh from the release
        folder into the proc folder.
        """

        sudo('cp %(release_path)s/settings.yaml %(proc_path)s/' % self.__dict__)
        sudo('cp %(release_path)s/env.sh %(proc_path)s/' % self.__dict__)

    def get_paths(self):
        """
        Return a dictionary of paths to be used when writing the proc config.
        Must include keys for 'home', 'tmp', 'settings', and 'envsh'.
        """
        return {
            'home': self.proc_tmp_path,
            'tmp': self.proc_tmp_path,
            'settings': self.yaml_settings_path,
            'envsh': self.envsh_path,
        }

    def get_wrapper_cmd(self):
        """
        Return the command that should be run to actually start up the process.
        """
        return 'exec %s' % self.proc_line

    def reload_supervisor(self):
        # For this to work, the host must have PROCS_ROOT/*/proc.conf in
        # the files include line in the main supervisord.conf
        sudo('supervisorctl reread')
        sudo('supervisorctl add ' + self.proc_name)

    def create_mount_points(self):
        # Make container mount points.  lxc will handle the actual mounts,
        # but we need to make the folders.
        for m in self.mountpoints:
            sudo('mkdir -p %s%s' % (self.proc_path, m))

    def write_proc_conf(self):
        if self.use_syslog:
            stdout_log = "syslog"
        else:
            stdout_log = posixpath.join(self.proc_path, 'log')
        proc_conf_vars = {
            'release_name': self.release_name,
            'proc': self.proc,
            'port': self.port,
            'proc_path': self.proc_path,
            'stdout_log': stdout_log,
            'user': self.get_proc_conf_user(),
            'release_path': self.release_path,
        }
        proc_conf_tmpl = get_template('proc.conf')
        remote_supd = posixpath.join(self.proc_path, 'proc.conf')
        files.upload_template(proc_conf_tmpl, remote_supd, proc_conf_vars,
                              use_sudo=True)

    def write_proc_lxc(self):
        # write the lxc config.
        if self.lxc_config_template:
            lxc_tmpl = get_template(self.lxc_config_template)
            remote_lxc_path = posixpath.join(self.proc_path, 'proc.lxc')
            files.upload_template(lxc_tmpl, remote_lxc_path, {
                'build_path': self.build_path,
                'proc_path': self.proc_path,
            }, use_sudo=True)

    def write_start_proc_sh(self):
        """
        Write the outer script that sets up the container.
        """
        sh_script = get_template('start_proc.sh')
        sh_remote = posixpath.join(self.proc_path, 'start_proc.sh')
        tmpl_data = {'cmd': self.get_wrapper_cmd()}
        files.upload_template(sh_script, sh_remote, tmpl_data, use_sudo=True)
        sudo('chmod +x %s' % sh_remote)

    def write_start_proc_inner(self):
        """
        Write the inner script that runs inside the container, loads up env
        vars, and actually starts the proc.
        """
        sh_script = get_template('proc.sh')
        sh_remote = posixpath.join(self.proc_path, 'proc.sh')
        tmpl_data = self.get_paths()
        tmpl_data['cmd'] = self.proc_line
        tmpl_data['port'] = self.port
        files.upload_template(sh_script, sh_remote, tmpl_data, use_sudo=True)
        sudo('chmod +x %s' % sh_remote)

    def get_proc_conf_user(self):
        # Uncontained procs are just executed by Supervisor directly, so
        # proc.conf needs to be configured with the real username that we want
        # to run as
        return self.user

    def create_proc_tmpdir(self):
        # Create a place for the proc to stick temporary files if it needs to.
        sudo('mkdir -p ' + self.proc_tmp_path)
        sudo('chown %s %s' % (self.user, self.proc_tmp_path))

    def get_proc_line(self):
        try:
            # Make a temporary copy of the Procfile for parsing.  Fetch it from
            # the host so we don't even need to have a local copy of the build
            # in order to add a new deploy of an existing release.
            tempdir = tempfile.mkdtemp()
            local_procfile = posixpath.join(tempdir, 'Procfile')
            get(posixpath.join(self.build_path, 'Procfile'), local_procfile)

            procs = parse_procfile(local_procfile)
            if not self.proc in procs:
                proc_names = ', '.join(procs.keys())
                raise KeyError("%s not found in Procfile (%s defined)" %
                               (self.proc, proc_names))
            # From the parsed Procfile, pull out the command that should be
            # used to start the actual proc.
            return procs[self.proc]
        finally:
            # Clean up our tempdir
            shutil.rmtree(tempdir)

    def upload_uptester(self):
        """
        Upload libraptor's "uptester" program to the proc root.
        """
        uptester = pkg_resources.resource_filename('raptor',
                                                   'uptester/uptester')
        remote_path = posixpath.join(self.proc_path, 'uptester')
        put(uptester, remote_path, use_sudo=True)
        sudo('chmod +x %s' % remote_path)


class ContainedDeployer(Deployer):

    def get_proc_conf_user(self):
        # Contained procs will be started by Supervisor as root, and then su to
        # be the configured user once inside the container.
        return 'root'

    def get_paths(self):
        """
        Return a dictionary of paths to be used when writing the proc config.
        Must include keys for 'home', 'tmp', 'settings', and 'envsh'.
        """
        # In a container, these paths are always the same.
        return {
            'home': '/app',
            'tmp': '/tmp',
            'settings': '/settings.yaml',
            'envsh': '/env.sh',
        }

    def get_wrapper_cmd(self):
        container_name = self.proc_name
        lxc_config_path = posixpath.join(self.proc_path, 'proc.lxc')
        return build_container_cmd('/proc.sh', self.user,
                                   container_name, lxc_config_path)


class PreciseDeployer(ContainedDeployer):
    mountpoints = ('/app',
                   '/bin',
                   '/dev',
                   '/etc',
                   '/lib',
                   '/lib64',
                   '/opt',
                   '/usr',
                   '/proc',
                   '/run',
                   '/sys',
                   '/dev/pts',)

    lxc_config_template = 'precise.lxc'


@task
def configure_proc(build_name, release_name, proc, port, user='nobody', use_syslog=False,
                   contain=False):
    if not contain:
        deployer_cls = Deployer
    else:
        issue = sudo('cat /etc/issue')
        if '12.04' in issue:
            deployer_cls = PreciseDeployer
        else:
            raise ValueError("Could not determine deployer type for %s" %
                             issue)
    deployer_cls(build_name, release_name, proc, port, user, use_syslog).run()


@task
def deploy_parcel(build_path, config_path, envsh_path, swarm,
                  proc, port, user='nobody', use_syslog=False, contain=False,
                  release_hash=None):
    # Builds have timstamps, but releases really don't care about them.  Two
    # releases created at different times with the same build and settings
    # should be treated the same.  So throw away the timestamp portion of the
    # build name when creating the release name.
    build_file = os.path.basename(build_path)
    nameparts = build_file.split('-')
    app_name = nameparts[0]
    version = nameparts[1]

    build_name = '-'.join([app_name, version])

    # A release name should look like gryphon-2.2.3-ldc-d5338b8a07, where the
    # random looking chars at the end come from a hash of the build tarball and
    # settings.yaml used for the release.
    if release_hash is None:
        chars = open(build_path, 'rb').read() + open(config_path, 'rb').read()
        release_hash = hashlib.md5(chars).hexdigest()[:8]
    release_name = '-'.join([app_name, version, swarm, release_hash])
    release_path = posixpath.join(RELEASES_ROOT, release_name)

    # Ensure that the proc path is written before the release is uploaded, to
    # prevent a race condition with the scooper.
    proc_name = '-'.join([release_name, proc, str(port)])
    proc_path = posixpath.join(PROCS_ROOT, proc_name)
    sudo('mkdir -p ' + proc_path)

    upload_release(build_path, build_name, config_path, release_path,
                   envsh_path, user=user)

    configure_proc(build_name, release_name, proc, port, user,
                   use_syslog=use_syslog, contain=contain)


def build_container_cmd(cmd, user, container_name, lxc_config_path):
    """
    Build up the shell command needed to launch a program inside a container.
    This is used both in deployments and launching the uptester.
    """
    # It's a bit redundant to source /env.sh here since it will also be done
    # inside proc.sh.  However, sourcing it here means that the uptester also
    # gets the same env vars without having to be launched from a proc.sh-like
    # inner wrapper script.
    tmpl = """exec lxc-start --name %(container_name)s -f %(lxc_config_path)s -- su --preserve-environment --shell /bin/bash -c "cd /app;source /env.sh; exec %(cmd)s" %(user)s"""
    return tmpl % vars()


def build_contained_uptests_command(proc_path, proc, host, port, user):
    """
    Build the command string for uptesting the given proc inside its lxc
    container.
    """
    cmd = "/uptester %(folder)s %(host)s %(port)s" % {
        'folder': posixpath.join('/app/uptests', proc),
        'host': host,
        'port': port,
    }
    container_name = posixpath.basename(proc_path) + '-uptest'
    lxc_config_path = posixpath.join(proc_path, 'proc.lxc')
    return build_container_cmd(cmd, user, container_name, lxc_config_path)


def build_uncontained_uptests_command(build_path, proc_path, proc, host,
                                      port, user):
    """
    Build the command string for uptesting a proc that's not inside an lxc
    container.
    """
    tmpl = """su -c "cd %(build_path)s;source %(envsh_path)s;%(uptester)s %(folder)s %(host)s %(port)s" %(user)s"""
    return tmpl % {
        'release_path': build_path,
        'folder': posixpath.join(build_path, 'uptests', proc),
        'host': host,
        'port': port,
        'user': user,
        'uptester': posixpath.join(proc_path, 'uptester'),
    }


def build_uptests_command(build_path, proc_path, proc, host, port, user):
    """
    Pick from the available uptest command builders based on what's present in
    the proc and build dirs.  Run that builder and return its result.
    """
    lxc_conf_path = posixpath.join(proc_path, 'proc.lxc')
    if files.exists(lxc_conf_path):
        return build_contained_uptests_command(proc_path, proc,
                                               env.host_string, port, user)
    else:
        return build_uncontained_uptests_command(build_path, proc_path, proc,
                                                 env.host_string, port, user)


@task
def ensure_uptester(proc_path):
    # If there's no uptester in the proc folder, put one there.
    uptester_path = posixpath.join(proc_path, 'uptester')
    uptester = pkg_resources.resource_filename('raptor', 'uptester/uptester')
    if files.exists(proc_path) and not files.exists(uptester_path):
        put(uptester, uptester_path, use_sudo=True)
        sudo('chmod +x %s' % uptester_path)


@task
def run_uptests(proc, user='nobody'):
    procdata = Proc.parse_name(proc)
    procname = procdata['proc_name']
    build_name = '%(app_name)s-%(version)s' % procdata
    build_path = posixpath.join(BUILDS_ROOT, build_name)
    proc_path = posixpath.join(PROCS_ROOT, proc)

    tests_path = posixpath.join(build_path, 'uptests', procname)
    try:
        ensure_uptester(proc_path)
        if files.exists(tests_path):
            # determine whether we're running contained or uncontained
            cmd = build_uptests_command(build_path, proc_path, procname,
                                        env.host_string, procdata['port'],
                                        user)

            result = sudo(cmd)
            # Though the uptester emits JSON to stdout, it's possible for the
            # container or env var setup to emit some other output before the
            # uptester even runs.  Stuff like this:

            # 'bash: /app/env.sh: No such file or directory'

            # Split that off and prepend it as an extra first uptest result.
            # Since results should be a JSON list, look for any characters
            # preceding the first square bracket.

            m = re.match('(?P<prefix>[^\[]*)(?P<json>.*)', result, re.S)

            # If the regular expression doesn't even match, return the raw
            # string.
            if m is None:
                return [{
                    'Passed': False,
                    'Name': 'uptester',
                    'Output': result,
                }]

            parts = m.groupdict()
            try:
                parsed = json.loads(parts['json'])
                if len(parts['prefix']):
                    parsed.insert(0, {
                        'Passed': False,
                        'Name': 'uptester',
                        'Output': parts['prefix']
                    })
                return parsed
            except ValueError:
                # If we still fail parsing the json, return a dict of our own
                # with all the output inside.
                return [{
                    'Passed': False,
                    'Name': 'uptester',
                    'Output': result
                }]
        else:
            return []

    except (Exception, SystemExit):
        # Fabric will raise SystemExit if we don't supply the right password
        # and abort_on_prompts is True.  Here we catch any exception raised
        # during the uptests and pass it back in the same format as other test
        # results.
        return [{
            'Name': None,
            'Output': traceback.format_exc(),
            'Passed': False,
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
    proc_dir = posixpath.join(PROCS_ROOT, proc)
    if files.exists(proc_dir):
        sudo('rm -rf %s' % proc_dir)


@task
def delete_release(release, releases_root=RELEASES_ROOT, procs_root=PROCS_ROOT,
                   cascade=False):
    procs = get_procs()

    releases_in_use = set(['%(app_name)s-%(version)s-%(config_name)s-%(hash)s' %
                           Proc.parse_name(p) for p in procs])

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
            raise SystemExit('NOT DELETING %s. Release is currently in use, '
                             'and cascade=False' % release)
    sudo('rm -rf %s/%s' % (releases_root, release))


@task
def delete_build(build, builds_root=BUILDS_ROOT, releases_root=RELEASES_ROOT,
                 procs_root=PROCS_ROOT, cascade=False):
    build_releases = get_build_releases(build)
    if len(build_releases):
        if not cascade:
            raise SystemExit("NOT DELETING %s. Build is currently in use, "
                             "and cascade=False" % build)
        else:
            for release in build_releases:
                delete_release(release, releases_root, procs_root, cascade)
    sudo('rm -rf %s/%s' % (builds_root, build))


@task
def clean_releases_folders(releases_root=RELEASES_ROOT, procs_root=PROCS_ROOT):
    """ Check in releases_root for releases not being used by procs, so we can
    clean them up.

    You may choose not to execute the actual delete (to test for example), and
    if you choose to be verbose it will print out the releases it will delete.
    """

    if files.exists(procs_root, use_sudo=True) and \
        files.exists(releases_root, use_sudo=True):
        procs = get_procs()
        releases = get_releases()
        releases_in_use = set([
            '%(app_name)s-%(version)s-%(config_name)s-%(hash)s' %
            Proc.parse_name(p) for p in procs])
        deleted = []
        for release in releases:
            if release not in releases_in_use:
                deleted.append(release)
                delete_release(release, releases_root, procs_root, False)
        colors.green("Cleaned up %i releases." % len(deleted))


def clean_builds_folders(builds_root=BUILDS_ROOT, releases_root=RELEASES_ROOT):
    """
    Check in builds_root for builds not being used by releases.
    """

    if files.exists(builds_root, use_sudo=True) and files.exists(releases_root,
                                                                 use_sudo=True):
        releases = get_releases()
        builds = set(get_builds())

        builds_in_use = set([release_to_build(r) for r in releases])
        unused_builds = builds.difference(builds_in_use)
        for build in unused_builds:
            delete_build(build, builds_root, releases_root)


@task
def get_procs(procs_root=PROCS_ROOT):
    """
    Return the names of all the procs on the host.
    """
    return sudo('ls -1 %s' % procs_root).split()


@task
def get_releases(releases_root=RELEASES_ROOT):
    """
    Return the names of all the releases on the host.
    """
    return sudo('ls -1 %s' % releases_root).split()


@task
def get_builds(builds_root=BUILDS_ROOT):
    """
    Return the names of all the builds on the host.
    """
    return sudo('ls -1 %s' % builds_root).split()


@task
def get_release_procs(release, release_root=RELEASES_ROOT, procs_root=PROCS_ROOT):
    """
    Given a release name, return a list of all the procs on the host that use
    that release.
    """
    procs = get_procs()
    def proc_to_release(proc):
        """
        Given a proc name, return the name of the release that it uses.
        """
        tmpl = '%(app_name)s-%(version)s-%(config_name)s-%(hash)s'
        return tmpl % Proc.parse_name(p)
    return [p for p in procs if proc_to_release(p)==release]


def release_to_build(release):
    """
    Given a release name, return the name of the build that it uses.
    """
    try:
        return "%s-%s" % tuple(release.split('-')[:2])
    except ValueError:
        return "unknown-unknown"

@task
def get_build_releases(build, builds_root=BUILDS_ROOT,
                       releases_root=RELEASES_ROOT):
    releases = get_releases()
    return [r for r in releases if release_to_build(r)==build]


@task
def clean_releases_and_builds():
    """
    Delete any releases not in use by procs on the host.

    Then delete any builds not in use by releases on the host.
    """
    clean_releases_folders(RELEASES_ROOT, PROCS_ROOT)

    clean_builds_folders(BUILDS_ROOT, RELEASES_ROOT)


class SSHConnection(object):
    """
    A context manager for creating a non-Fabric SSH connection with a username and
    password, then ensuring it gets cleaned up.

    You can also instantiate this object without using it as a context manager.
    If you do, it's up to you to call close() when you're done.
    """
    # This class began life with grand ambitions to be a Fabric replacement.
    # Then I realized how much ugliness Fabric was hiding from me.  Now this
    # class is just used for writing the settings.yaml file inside a release,
    # because Fabric jobs would delete each other's temp files if two workers
    # happened to try deploying the same file at the same time
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
