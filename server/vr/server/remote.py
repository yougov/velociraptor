"""
Utilities for running commands and reading/writing files on remote hosts over
SSH.
"""

import traceback
import posixpath
import pkg_resources
import json
import re
import contextlib

import yaml
from fabric.api import (sudo as sudo_, get, put, task, env, settings as
                        fab_settings)
from fabric.contrib import files
from fabric.context_managers import cd

from vr.common.models import ProcData
from vr.common.paths import (BUILDS_ROOT, PROCS_ROOT, get_proc_path,
                             get_container_name, get_container_path)
from vr.common.utils import randchars
from vr.builder.main import BuildData

from vr.server.models import Host

def get_template(name):
    return pkg_resources.resource_filename('vr.common', 'templates/' + name)


class Error(Exception):
    """
    An exception representing a remote command error.
    """
    def __init__(self, out):
        self.out = out
        super(Error, self).__init__(out)

    @property
    def title(self):
        return ("Command failed with exit code {self.return_code}: "
            "{self.command}".format(self=self))

    def __getattr__(self, attr):
        return getattr(self.out, attr)

    @classmethod
    def handle(cls, out):
        if out.failed:
            raise cls(out)
        return out


def sudo(*args, **kwargs):
    """
    Wrap fabric's sudo to trap errors and raise them.
    """
    kwargs.setdefault('warn_only', True)
    return Error.handle(sudo_(*args, **kwargs))


@task
def deploy_proc(proc_yaml_path):
    """
    Given a path to a proc.yaml file, get that proc set up on the remote host.
    The runner's "setup" command will do most of the work.
    """
    settings = load_proc_data(proc_yaml_path)
    proc_path = get_proc_path(settings)
    sudo('mkdir -p ' + proc_path)

    remote_proc_yaml = posixpath.join(proc_path, 'proc.yaml')
    put(proc_yaml_path, remote_proc_yaml, use_sudo=True)

    sudo(get_runner(settings) + ' setup ' + remote_proc_yaml)
    write_proc_conf(settings)
    sudo('supervisorctl reread')
    sudo('supervisorctl add ' + get_container_name(settings))


def write_proc_conf(settings):
    proc_path = get_proc_path(settings)
    proc_conf_vars = {
        'proc_yaml_path': posixpath.join(proc_path, 'proc.yaml'),
        'container_name': get_container_name(settings),
        'container_path': get_container_path(settings),
        'log': posixpath.join(proc_path, 'log'),
        'runner': get_runner(settings),
        'user': 'root',
    }
    proc_conf_tmpl = get_template('proc.conf')
    files.upload_template(
        proc_conf_tmpl,
        posixpath.join(proc_path, 'proc.conf'),
        proc_conf_vars,
        use_sudo=True)


@task
def run_uptests(hostname, proc_name, user='nobody'):
    host = Host.objects.get(name=hostname)
    proc = host.get_proc(proc_name)
    settings = proc.settings
    if settings is None:
        print('{0.name} (pid {0.pid}) running on {0.hostname} '
              'is not a VR process.  Skipping...'.format(proc))
        return

    proc_path = get_proc_path(settings)

    new_container_path = posixpath.join(proc_path, 'rootfs')
    if files.exists(new_container_path, use_sudo=True):
        tests_path = posixpath.join(new_container_path, 'app/uptests',
                                    settings.proc_name)
    else:
        build_path = get_build_path(settings)
        tests_path = posixpath.join(build_path, 'uptests', settings.proc_name)
    try:
        if files.exists(tests_path, use_sudo=True):

            # Containers set up by new-style 'runners' will be in a 'rootfs'
            # subpath under the proc_path.  Old style containers are right in
            # the proc_path.  We have to launch the uptester slightly
            # differently
            if files.exists(new_container_path, use_sudo=True):
                proc_yaml_path = posixpath.join(proc_path, 'proc.yaml')
                cmd = get_runner(settings) + ' uptest ' + proc_yaml_path
            else:
                cmd = legacy_uptests_command(proc_path, settings.proc_name,
                                             env.host_string, settings.port,
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

    except Error as error:
        # An error occurred in the command invocation, including if an
        # incorrect password is supplied and abort_on_prompts is True.
        return [{
            'Name': None,
            'Output': error.out,
            'Passed': False,
        }]

    except Exception:
        # Catch any other exception raised
        # during the uptests and pass it back in the same format as other test
        # results.
        return [{
            'Name': None,
            'Output': traceback.format_exc(),
            'Passed': False,
        }]


def legacy_uptests_command(proc_path, proc, host, port, user):
    """
    Build the command string for uptesting the given proc inside its lxc
    container.
    """
    cmd = "/uptester %(folder)s %(host)s %(port)s" % {
        'folder': posixpath.join('/app/uptests', proc),
        'host': host,
        'port': port,
    }
    tmpl = """exec lxc-start --name %(container_name)s -f %(lxc_config_path)s -- su --preserve-environment --shell /bin/bash -c "cd /app;source /env.sh; exec %(cmd)s" %(user)s"""
    return tmpl % {
        'cmd': cmd,
        'user': user,
        'container_name': posixpath.basename(proc_path) + '-uptest',
        'lxc_config_path': posixpath.join(proc_path, 'proc.lxc'),
    }

@task
def delete_proc(hostname, proc):
    if not proc:
        raise SystemExit("You must supply a proc name")
    host = Host.objects.get(name=hostname)
    settings = host.get_proc(proc).settings

    # stop the proc
    sudo('supervisorctl stop %s' % proc)
    # remove the proc
    sudo('supervisorctl remove %s' % proc)

    proc_dir = posixpath.join(PROCS_ROOT, proc)

    proc_yaml_path = posixpath.join(proc_dir, 'proc.yaml')
    if files.exists(proc_yaml_path, use_sudo=True):
        sudo(get_runner(settings) + ' teardown ' + proc_yaml_path)

    # delete the proc dir
    if files.exists(proc_dir, use_sudo=True):
        sudo('rm -rf %s' % proc_dir)


def proc_to_build(proc):
    parts = proc.split('-')
    return '-'.join(parts[:2])


def get_build_procs(build):
    """
    Given a build name like "some_app-v3", return a list of all the folders in
    /apps/procs that are using that build.
    """
    allprocs = get_procs()
    # Rely on the fact that proc names start with app-version, same as a build.

    return [p for p in allprocs if proc_to_build(p) == build]


@task
def delete_build(build, cascade=False):
    build_procs = get_build_procs(build)
    if len(build_procs):
        if not cascade:
            raise SystemExit("NOT DELETING %s. Build is currently in use, "
                             "and cascade=False" % build)
        else:
            for proc in build_procs:
                delete_proc(proc)
    sudo('rm -rf %s/%s' % (BUILDS_ROOT, build))


def clean_builds_folders():
    """
    Check in builds_root for builds not being used by releases.
    """

    if files.exists(BUILDS_ROOT, use_sudo=True):
        procs = get_procs()
        builds = set(get_builds())

        builds_in_use = set([proc_to_build(p) for p in procs])
        unused_builds = builds.difference(builds_in_use)
        for build in unused_builds:
            delete_build(build)


@task
def get_procs():
    """
    Return the names of all the procs on the host.
    """
    procs = sudo('ls -1 ' + PROCS_ROOT).split('\n')
    # filter out any .hold files
    return [p for p in procs if not p.endswith('.hold')]


@task
def get_builds():
    """
    Return the names of all the builds on the host.
    """
    return sudo('ls -1 %s' % BUILDS_ROOT).split()


@task
def build_app(build_yaml_path):
    """
    Given the path to a build.yaml file with everything you need to make a
    build, copy it to the remote host and run the vbuild tool on it.  Then copy
    the resulting build.tar.gz and build_result.yaml back up here.
    """
    remote_tmp = '/tmp/' + randchars()
    sudo('mkdir -p ' + remote_tmp)
    with cd(remote_tmp):
        try:
            remote_build_yaml_path = posixpath.join(remote_tmp, 'build_job.yaml')
            put(build_yaml_path, remote_build_yaml_path, use_sudo=True)
            sudo('vbuild build ' + remote_build_yaml_path)
            # relies on the build being named build.tar.gz and the manifest being named
            # build_result.yaml.
            get(posixpath.join(remote_tmp, 'build_result.yaml'),
                'build_result.yaml')
            with open('build_result.yaml', 'rb') as f:
                BuildData(yaml.safe_load(f))
            get(posixpath.join(remote_tmp, 'build.tar.gz'), 'build.tar.gz')
        finally:
            try:
                # try to get compile.log even if build fails.
                with fab_settings(warn_only=True):
                    get(posixpath.join(remote_tmp, 'compile.log'), 'compile.log')
            except:
                print "Could not retrieve compile.log"
            finally:
                sudo('rm -rf ' + remote_tmp)


@contextlib.contextmanager
def shell_env(**env_vars):
    """
    A context that updates the shell to add environment variables.
    Ref http://stackoverflow.com/a/8454134/70170
    """
    orig_shell = env['shell']
    env_vars_str = ' '.join(
        '{key}={value}'.format(**vars())
        for key, value in env_vars.items()
    )
    if env_vars:
        env['shell'] = '{env_vars_str} {orig_shell}'.format(
            env_vars_str=env_vars_str,
            orig_shell=env['shell'],
        )
    try:
        yield
    finally:
        env['shell'] = orig_shell


def load_proc_data(proc_yaml_path):
    with open(proc_yaml_path, 'rb') as f:
        return ProcData(yaml.safe_load(f))


def get_build_path(settings):
    build_name = '{0.app_name}-{0.version}-{0.image_name}'.format(settings)
    return posixpath.join(BUILDS_ROOT, build_name)


def get_runner(settings):
    """
    Return the appropriate VR runner command to use with the given settings.
    """
    return 'vrun' if settings.image_url is not None else 'vrun_precise'
