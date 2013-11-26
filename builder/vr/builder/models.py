import os
import pwd
import hashlib
import logging
import shutil

import yaml
import utc

from vr.common import repo
from vr.common.utils import run, mkdir, lock_file
from vr.common.paths import VR_ROOT

from vr.builder.slugignore import clean_slug_dir

# If we're root, and RAPTOR_HOME hasn't been set, then put all checkouts in
# /apps/builder

me = pwd.getpwuid(os.getuid()).pw_name

if 'RAPTOR_HOME' in os.environ:
    HOME = os.environ['RAPTOR_HOME']
elif pwd.getpwuid(os.getuid()).pw_name == 'root':
    HOME = os.path.join(VR_ROOT, 'builder')
else:
    HOME = os.path.expanduser('~/.raptor')
PACKS_HOME = os.path.join(HOME, 'buildpacks')
CACHE_HOME = os.path.join(HOME, 'cache')
BUILD_HOME = os.path.join(HOME, 'build')
REPO_HOME = os.path.join(HOME, 'repo')
TARBALL_HOME = os.path.join(HOME, 'tarballs')
OUTPUT_HOME = os.path.join(HOME, 'output')
LOCKS_HOME = os.path.join(HOME, 'locks')


log = logging.getLogger(__name__)


class BuildPack(repo.Repo):

    def detect(self, app):
        """
        Given an app, run detect script on it to determine whether it can be
        built with this pack.  Return True/False.
        """
        script = os.path.join(self.folder, 'bin', 'detect')
        cmd = '%s %s' % (script, app.folder)
        result = run(cmd)
        return result.status_code == 0

    def compile(self, app):
        log.info(
            'Compiling {app.basename} with {self.basename}'
            .format(**vars())
        )
        script = os.path.join(self.folder, 'bin', 'compile')

        cache_folder = os.path.join(CACHE_HOME, get_unique_repo_folder(app.url))

        cmd = ' '.join([script, app.folder, cache_folder])
        log.info(cmd)
        result = run(cmd, verbose=True)
        result.raise_for_status()

    def release(self, app):
        script = os.path.join(self.folder, 'bin', 'release')
        result = run('%s %s' % (script, app.folder))
        assert result.status_code == 0, ("Failed release on %s with %s "
                                         "buildpack" % (app, self.basename))
        return yaml.safe_load(result.output)

    def update(self, rev=None):
        """
        Override Repo.update to provide default rev when none is provided.
        """

        rev = rev or self.fragment or {
            'git': 'HEAD',
            'hg': 'tip',
        }[self.vcs_type]

        return super(BuildPack, self).update(rev)


class App(repo.Repo):
    """
    A Repo that contains a buildpack-compatible project.
    """

    def __init__(self, folder, url=None, buildpack=None, **kwargs):
        # remember kwargs for copying self later.
        self._kwargs = kwargs
        super(App, self).__init__(folder, url, **kwargs)
        # If buildpack is None here, we'll try self.detect_buildpack later.
        self._buildpack = buildpack

    def slugignore(self):
        clean_slug_dir(self.folder)

    def tar(self, appname, appversion):
        """
        Given an app name and version to be used in the tarball name,
        create a tar.bz2 file with all of this folder's contents inside.

        Return a Build object with attributes for appname, appversion,
        time, and path.
        """
        name_tmpl = '%(app)s-%(version)s-%(time)s.tar.bz2'
        time = utc.now()
        name = name_tmpl % {'app': appname,
                            'version': appversion,
                            'time': time.strftime('%Y-%m-%dT%H-%M')}

        if not os.path.exists(TARBALL_HOME):
            os.mkdir(TARBALL_HOME)
        tarball = os.path.join(TARBALL_HOME, name)
        tar_params = {'filename': tarball, 'folder': self.folder}
        tar_result = run('tar -C %(folder)s -cjf %(filename)s .' % tar_params)
        tar_result.raise_for_status()
        return Build(appname, appversion, time, tarball)


class Build(object):
    """
    A bundle of data about a completed build tarball.
    """
    def __init__(self, appname, appversion, time, path):
        self.appname = appname
        self.appversion = appversion
        self.time = time
        self.path = path


class lock_or_wait(object):
    """
    On init, provide a directory for creating lock files, and the name of some
    string you're locking (like a url).

    On enter, hash the string to get a filename, and open and lock the file.

    On exit, close the file.
    """
    def __init__(self, target, folder=LOCKS_HOME):
        self.folder = folder
        self.target = target

    def __enter__(self):
        path = os.path.join(self.folder, hashlib.md5(self.target).hexdigest())
        mkdir(self.folder)
        self.f = open(path, 'wb')
        lock_file(self.f)

    def __exit__(self, type, value, traceback):
        self.f.close()


def update_buildpack(url, packs_dir=PACKS_HOME, vcs_type=None):
    dest = os.path.join(packs_dir, repo.basename(url))
    # TODO: check for whether the buildpack in the folder is really the same as
    # the one we've been asked to add.
    mkdir(packs_dir)
    bp = BuildPack(dest, url, vcs_type=vcs_type)
    bp.update()
    return bp


def update_app(name, url, version, repos_dir=REPO_HOME, vcs_type=None):
    dest = os.path.join(repos_dir, name)
    mkdir(repos_dir)
    app = App(dest, url, vcs_type=vcs_type)
    app.update(version)
    return app


def get_unique_repo_folder(repo_url):
    """
    Given a repository URL, return a folder name that's human-readable,
    filesystem-friendly, and guaranteed unique to that repo.
    """
    return '%s-%s' % (repo.basename(repo_url), hashlib.md5(repo_url).hexdigest())


def get_build_folder(app_url):
    return os.path.join(BUILD_HOME, get_unique_repo_folder(app_url))


def get_repo_folder(repo_url):
    return os.path.join(REPO_HOME, get_unique_repo_folder(repo_url))


class use_buildfolder(object):
    """Context manager for putting you into an app-specific build directory on
    enter and returning you to where you started on exit.
    """
    def __init__(self, app_url):
        self.app_url = app_url
        self.orig_path = os.getcwd()
        self.temp_path = get_build_folder(self.app_url)

    def __enter__(self):
        if not os.path.isdir(self.temp_path):
            os.makedirs(self.temp_path, 0o770)
        os.chdir(self.temp_path)
        return self.temp_path

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)
        # Delete build folder when we're done.
        shutil.rmtree(self.temp_path)
