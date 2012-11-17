"""
Utilities for running commands and reading/writing files on remote hosts over
SSH.
"""

import os
import sys
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

# TODO: Change these to /apps/ so that we don't have YG-isms in the code and
# can more safely bind-mount /opt into app environments.  It's tricky, because
# cleanup code will have to check both the old and new locations when it runs.
# OR we do a one-time migration.
PROCS_ROOT = '/opt/yg/procs'
RELEASES_ROOT = '/opt/yg/releases'


@task
def upload_release(build_path, config_path, release_path, envsh_path, user='nobody'):
    # TODO: accept env_path that points to an env.sh file that can be sourced
    # by the proc at startup to provide env vars.

    remote_procfile = posixpath.join(release_path, 'Procfile')

    if files.exists(remote_procfile):
        colors.green('%s already on server.  No need to upload.' % remote_procfile)
        return

    colors.green('Creating remote directory')
    sudo('mkdir -p ' + release_path)

    colors.green('Uploading build')
    # Make a random filename for the remote tmp file.
    rname = ''.join(random.choice(string.ascii_letters) for x in xrange(20))
    remote_build_path = posixpath.join('/tmp', rname)
    put(build_path, remote_build_path, use_sudo=True)

    colors.green('Unpacking build')

    tar_cmd = 'tar xjf {remote_build_path} -C {release_path} --strip-components 1'
    tar_cmd = tar_cmd.format(**vars())
    sudo(tar_cmd)
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
        ssh.put_file(envsh_path, posixpath.join(release_path, 'env.sh'),
                     owner=user)

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


def get_template(name):
    here = os.path.dirname(__file__)
    return os.path.join(here, 'templates', name)


class Deployment(object):
    def __init__(self, release_name, proc, port, user, use_syslog, contain):
        self.release_name = release_name
        self.proc = proc
        self.port = port
        self.user = user
        self.use_syslog = use_syslog
        self.contain = contain
        self.proc_name = '-'.join([release_name, proc, str(port)])
        self.proc_path = posixpath.join(PROCS_ROOT, self.proc_name)
        self.proc_tmp_path = posixpath.join(self.proc_path, 'tmp')
        self.release_path = posixpath.join(RELEASES_ROOT, self.release_name)
        self.envsh_path = posixpath.join(self.release_path, 'env.sh')
        self.yaml_settings_path = posixpath.join(self.release_path,
                                                 "settings.yaml")
        self.proc_line = self.get_proc_line()

    def run(self):

        sudo('mkdir -p ' + self.proc_path)

        self.write_proc_conf()
        self.write_start_proc_sh()
        self.create_proc_tmpdir()
        self.upload_uptester()

        if self.contain:
            # Make container mount points.  lxc will handle the actual mounts,
            # but we need to make the mount points.
            mountpoints = ('/app', '/bin', '/dev', '/etc', '/lib', '/lib64',
                           '/opt', '/usr', '/proc')
            for m in mountpoints:
                sudo('mkdir -p %s%s' % (self.proc_path, m))

        # For this to work, the host must have PROCS_ROOT/*/proc.conf in
        # the files include line in the main supervisord.conf
        sudo('supervisorctl reread')
        sudo('supervisorctl add ' + self.proc_name)

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
            'user': 'root' if self.contain else self.user,
            'release_path': self.release_path,
        }
        proc_conf_tmpl = get_template('proc.conf')
        remote_supd = posixpath.join(self.proc_path, 'proc.conf')
        files.upload_template(proc_conf_tmpl, remote_supd, proc_conf_vars,
                              use_sudo=True)

    def write_start_proc_sh(self):
        if self.contain:
            sh_script = get_template('start_contained.sh')
            # write the lxc config.
            lxc_tmpl = get_template('proc.lxc')
            remote_lxc_path = posixpath.join(self.proc_path, 'proc.lxc')
            files.upload_template(lxc_tmpl, remote_lxc_path, {
                'proc_path': self.proc_path,
                'release_path': self.release_path,
            }, use_sudo=True)
        else:
            sh_script = get_template('start_proc.sh')

        sh_remote = posixpath.join(self.proc_path, 'start_proc.sh')
        files.upload_template(sh_script, sh_remote, {
            'envsh_path': '/app/env.sh' if self.contain else self.envsh_path,
            'settings_path': self.release_path + "/settings.yaml",
            'port': self.port,
            'cmd': self.proc_line,
            'tmpdir': self.proc_tmp_path,
            'proc_name': self.proc_name,
            'procs_root': PROCS_ROOT,
            'user': self.user,
        }, use_sudo=True)
        sudo('chmod +x %s' % sh_remote)

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
            get(posixpath.join(self.release_path, 'Procfile'), local_procfile)

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


@task
def configure_proc(release_name, proc, port, user='nobody', use_syslog=False,
                   contain=False):

    d = Deployment(release_name, proc, port, user, use_syslog, contain)
    d.run()


@task
def deploy_parcel(build_path, config_path, envsh_path, recipe, proc, port,
                  user='nobody', use_syslog=False, contain=False,
                  release_hash=None):
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
    if release_hash is None:
        chars = open(build_path, 'rb').read() + open(config_path, 'rb').read()
        release_hash = hashlib.md5(chars).hexdigest()[:8]
    release_name = '-'.join([app_name, version, recipe, release_hash])
    release_path = posixpath.join(RELEASES_ROOT, release_name)


    # Ensure that the proc path is written before the release is uploaded, to
    # prevent a race condition with the scooper.
    proc_name = '-'.join([release_name, proc, str(port)])
    proc_path = posixpath.join(PROCS_ROOT, proc_name)
    sudo('mkdir -p ' + proc_path)

    upload_release(build_path, config_path, release_path, envsh_path)

    configure_proc(release_name, proc, port, user, use_syslog=use_syslog,
                   contain=contain)


def parse_procname(proc):
    app, version, profile, release_hash, procname, port = proc.split('-')
    return vars()


def build_contained_uptests_command(proc_path, proc, host, port, user):
    """
    Build the command string for uptesting the given proc inside its lxc
    container.
    """
    tmpl = """lxc-start --name %(procname)s-uptest -f %(lxc_config)s -- su --preserve-environment -c "cd /app;source /app/env.sh; exec /uptester %(folder)s %(host)s %(port)s" %(user)s"""
    return tmpl % {
        'procname': posixpath.basename(proc_path),
        'lxc_config': posixpath.join(proc_path, 'proc.lxc'),
        'folder': posixpath.join('/app/uptests', proc),
        'host': host,
        'port': port,
        'user': user,
    }


def build_uncontained_uptests_command(release_path, proc_path, proc, host,
                                      port, user):
    """
    Build the command string for uptesting a proc that's not inside an lxc
    container.
    """
    tmpl = """su -c "cd %(release_path)s;source %(envsh_path)s;%(uptester)s %(folder)s %(host)s %(port)s" %(user)s"""
    return tmpl % {
        'release_path': release_path,
        'envsh_path': posixpath.join(release_path, 'env.sh'),
        'folder': posixpath.join(release_path, 'uptests', proc),
        'host': host,
        'port': port,
        'user': user,
        'uptester': posixpath.join(proc_path, 'uptester'),
    }


def build_legacy_uptests_command(release_path, proc_path, proc, host, port,
                                 user):
    tmpl = """su -c "cd %(release_path)s;%(env_vars)s;%(uptester)s %(folder)s %(host)s %(port)s" %(user)s"""
    env_vars = ('APP_SETTINGS_YAML=%(settings_path)s PATH=%(env_bin)s:$PATH'
        % {
            'settings_path': posixpath.join(release_path, 'settings.yaml'),
            'env_bin': posixpath.join(release_path, 'env', 'bin'),
        })
    return tmpl % {
        'release_path': release_path,
        'env_vars': env_vars,
        'folder': posixpath.join(release_path, 'uptests', proc),
        'host': host,
        'port': port,
        'user': user,
        'uptester': posixpath.join(proc_path, 'uptester'),
    }


def build_uptests_command(release_path, proc_path, proc, host, port, user):
    """
    Pick from the available uptest command builders based on what's present in
    the proc and release dirs.  Run that builder and return its result.
    """
    lxc_conf_path = posixpath.join(proc_path, 'proc.lxc')
    envsh_path = posixpath.join(release_path, 'env.sh')
    if files.exists(lxc_conf_path):
        return build_contained_uptests_command(proc_path, proc,
                                              env.host_string,
                                              port, user)
    elif files.exists(envsh_path):
        return build_uncontained_uptests_command(release_path,
                                                proc_path, proc,
                                                env.host_string,
                                                port, user)

    return build_legacy_uptests_command(release_path,
                                                proc_path, proc,
                                                env.host_string,
                                                port, user)


@task
def ensure_uptester(proc_path):
    # If there's no uptester in the proc folder, put one there.
    uptester_path = posixpath.join(proc_path, 'uptester')
    if not files.exists(uptester_path):
        uptester = pkg_resources.resource_filename('raptor',
                                                   'uptester/uptester')
        put(uptester, uptester_path, use_sudo=True)
        sudo('chmod +x %s' % uptester_path)


@task
def run_uptests(proc, user='nobody'):
    procdata = parse_procname(proc)
    procname = procdata['procname']
    release_path = posixpath.join(RELEASES_ROOT,
                                  '%(app)s-%(version)s-%(profile)s-%(release_hash)s'
                                  % procdata)
    procdata['release_path'] = release_path
    proc_path = posixpath.join(PROCS_ROOT, proc)
    tests_path = posixpath.join(release_path, 'uptests', procname)
    try:
        ensure_uptester(proc_path)
        if files.exists(tests_path):
            # determine whether we're running contained or uncontained
            cmd = build_uptests_command(release_path, proc_path,
                                                    procname, env.host_string,
                                                    procdata['port'], user)

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
        exc_type, exc_value, exc_sraceback = sys.exc_info()
        return [{
            'Name': None,
            'Output': traceback.format_exc(),
            'Passed': False,
        }]


@task
def delete_proc(proc):
    # TODO: support checking in the /opt/yg/releases and /opt/yg/procs legacy
    # locations so we have a clean migration path.
    if not proc:
        raise SystemExit("You must supply a proc name")
    # stop the proc
    sudo('supervisorctl stop %s' % proc)
    # remove the proc
    sudo('supervisorctl remove %s' % proc)

    # delete the proc dir
    proc_dir = posixpath.join(PROCS_ROOT, proc)
    sudo('rm -rf %s' % proc_dir)


@task
def delete_release(release, cascade=False):
    # TODO: support checking in the /opt/yg/releases and /opt/yg/procs legacy
    # locations so we have a clean migration path.
    procs = sudo('ls -1 %s' % PROCS_ROOT).split()

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
    sudo('rm -rf %s/%s' % (RELEASES_ROOT, release))


@task
def clean_releases(execute=True):
    """ Check in RELEASES_ROOT for releases not being used by procs, so we can
    clean them up.

    You may choose not to execute the actual delete (to test for example), and
    if you choose to be verbose it will print out the releases it will delete.

    Finally if one of the directory doesn't exist we return raise a SystemExit.
    """

    # TODO: support checking in the /opt/yg/releases and /opt/yg/procs legacy
    # locations so we have a clean migration path.
    if files.exists(PROCS_ROOT, use_sudo=True) and \
        files.exists(RELEASES_ROOT, use_sudo=True):
        procs = sudo('ls -1 %s' % PROCS_ROOT).split()
        releases = sudo('ls -1 %s' % RELEASES_ROOT).split()
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
        raise SystemExit("Either %s or %s doesn't exist" % (PROCS_ROOT,
                                                            RELEASES_ROOT))


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
