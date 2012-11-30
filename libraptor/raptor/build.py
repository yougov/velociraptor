import os
import subprocess
import hashlib

import yaml
import envoy

from raptor import repo


HOME = (os.environ.get('RAPTOR_HOME') or os.path.expanduser('~/.raptor'))
PACKS_HOME = os.path.join(HOME, 'buildpacks')
CACHE_HOME = os.path.join(HOME, 'cache')
CONFIG_FILE = os.path.join(HOME, 'config.yaml')


class BuildPack(repo.Repo):

    def detect(self, app):
        """
        Given an app, run detect script on it to determine whether it can be
        built with this pack.  Return True/False.
        """
        script = os.path.join(self.folder, 'bin', 'detect')
        cmd = '%s %s' % (script, app.folder)
        result = envoy.run(cmd)
        return result.status_code == 0

    def compile(self, app):
        script = os.path.join(self.folder, 'bin', 'compile')

        app_url_hash = hashlib.md5(app.url).hexdigest()
        cache_folder = os.path.join(CACHE_HOME, '%s-%s' % (self.basename,
                                                           app_url_hash))

        # use ordinary subprocess here instead of envoy because we want stdout
        # to be printed to the terminal.
        retcode = subprocess.call([script, app.folder, cache_folder])
        assert retcode == 0, ("Failed compiling %s with %s buildpack" % (app,
                                                                         self.basename))

    def release(self, app):
        script = os.path.join(self.folder, 'bin', 'release')
        result = envoy.run('%s %s' % (script, app.folder))
        assert result.status_code == 0, ("Failed release on %s with %s "
                                         "buildpack" % (app, self.basename))
        return yaml.safe_load(result.std_out)


class App(repo.Repo):
    """
    A Repo that contains a buildpack-compatible project.
    """

    def __init__(self, folder, url=None, buildpack=None, buildpack_order=None, *args,
                 **kwargs):
        super(App, self).__init__(folder, url, *args, **kwargs)
        # If buildpack is None here, we'll try self.detect_buildpack later.
        self._buildpack = buildpack
        self.buildpack_order = (buildpack_order or
                                get_config().get('buildpack_order'))

    def detect_buildpack(self):
        """
        Loop over installed build packs and run each one's 'detect' script on
        the project until one succeeds, and set as self.buildpack.  Raise
        exception if nothing matches.
        """
        detected = next(
            (bp for bp in list_buildpacks(preferred_order=self.buildpack_order)
             if bp.detect(self)), None)
        if detected is None:
            raise ValueError("Cannot determine app's buildpack.")
        return detected

    @property
    def buildpack(self):
        if not self._buildpack:
            self._buildpack = self.detect_buildpack()
        return self._buildpack

    def compile(self):
        self.buildpack.compile(self)

    def release(self):
        return self.buildpack.release(self)


def list_buildpacks(packs_dir=PACKS_HOME, preferred_order=None):

    preferred_order = preferred_order or None
    # if we have a preferred_order, then use that first, and filesystem order
    # second.
    buildpacks = os.listdir(packs_dir)
    if preferred_order:
        # This is inefficient.  It doesn't matter.
        new = []
        for bp in preferred_order:
            if bp in buildpacks:
                # something from the configured order is installed.  Append to
                # new list so it's in proper position, and delete from old
                # list.
                new.append(bp)
                buildpacks.remove(bp)
        # Anything left in 'buildpacks' must not have been specified in the
        # configured order, so just tack it on at the end
        new.extend(buildpacks)
        buildpacks = new

    return [BuildPack(os.path.join(packs_dir, d)) for d in buildpacks]


def add_buildpack(url, packs_dir=PACKS_HOME, vcs_type=None):
    # Check whether the pack exists
    dest = os.path.join(packs_dir, repo.basename(url))
    # If folder already exists, assume that we've already checked out the
    # buildpack there.
    # TODO: check for whether the buildpack in the folder is really the same as
    # the one we've been asked to add.
    if not os.path.exists(packs_dir):
        envoy.run('mkdir -p %s' % packs_dir)
    bp = BuildPack(dest, url, vcs_type=vcs_type)
    bp.update()
    return bp


def get_config(file_path=CONFIG_FILE):
    try:
        with open(file_path, 'rb') as f:
            return yaml.safe_load(f)
    except IOError:
        return {}
