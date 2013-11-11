import os
import stat
import hashlib
import shutil
import subprocess
import pkg_resources
import tarfile

import yaml

from vr.common.utils import tmpdir, mkdir, randchars, file_md5, chowntree
from vr.builder.models import (BuildPack, update_buildpack, update_app,
                               lock_or_wait, CACHE_HOME, OUTPUT_HOME)
from vr.common.models import ProcData
from vr.common.paths import get_container_path
from vr.builder.slugignore import clean_slug_dir


def cmd_build(build_data, runner_cmd='run', make_tarball=True):
    # runner_cmd maybe be 'run' or 'shell'.

    outfolder = os.getcwd()

    # As long as we're sometimes using vrun_precise, which bind-mounts
    # system folders into the container, it's not safe to run a build as
    # root, because then untrusted code in the app or buildpack could run
    # amok.  If we ever switch entirely to image-based builds, that could
    # change.
    user = 'nobody'

    with tmpdir() as here:

        # Only bother pulling all the buildpacks if the build file doesn't specify
        # a particular one to build with.
        buildpack_url = getattr(build_data, 'buildpack_url', None)
        buildpack_folders = []
        if not buildpack_url:
            buildpack_folders = pull_buildpacks(build_data.buildpack_urls)

        # clone/pull repo to latest
        app_folder = pull_app(build_data.app_name,
                              build_data.app_repo_url,
                              build_data.version,
                              vcs_type=build_data.app_repo_type)
        chowntree(app_folder, username=user)


        volumes = [
            [os.path.join(here, app_folder), '/build']
        ]

        if buildpack_url:
            folder = pull_buildpack(buildpack_url)
            env = {'BUILDPACK_DIR': '/' + folder}
            volumes.append([os.path.join(here, folder), '/' + folder])
        else:
            buildpacks_env = ':'.join('/' + bp for bp in buildpack_folders)
            env = {'BUILDPACK_DIRS': buildpacks_env}
            for folder in buildpack_folders:
                volumes.append([os.path.join(here, folder), '/' + folder])

        cachefolder = os.path.join(CACHE_HOME, app_folder)
        if os.path.isdir(cachefolder):
            with lock_or_wait(cachefolder):
                shutil.copytree(cachefolder, 'cache', symlinks=True)
        else:
            mkdir('cache')
            # Maybe we're on a brand new host that's never had CACHE_HOME
            # created.  Ensure that now.
            mkdir(CACHE_HOME)
        chowntree('cache', username=user)
        volumes.append([os.path.join(here, 'cache'), '/cache'])

        buildproc = ProcData({
            'app_name': build_data.app_name,
            'app_repo_url': '',
            'app_repo_type': '',
            'buildpack_url': '',
            'buildpack_version': '',
            'config_name': 'build',
            'env': env,
            'host': '',
            'port': 0,
            'version': build_data.version,
            'release_hash': '',
            'settings': {},
            'user': user,
            'cmd': '/builder.sh /build /cache',
            'volumes': volumes,
            'proc_name': 'build',
            'image_name': build_data.image_name,
            'image_url': build_data.image_url,
            'image_md5': build_data.image_md5,
        })

        # write a proc.yaml for the container.
        with open('buildproc.yaml', 'wb') as f:
            f.write(buildproc.as_yaml())

        if build_data.image_url is None:
            runner = 'vrun_precise'
        else:
            runner = 'vrun'

        try:
            subprocess.check_call([runner, 'setup', 'buildproc.yaml'])
            # copy the builder.sh script into place.
            script_src = pkg_resources.resource_filename('vr.builder',
                                                     'scripts/builder.sh')
            script_dst = os.path.join(get_container_path(buildproc),
                                      'builder.sh')
            shutil.copy(script_src, script_dst)
            # Make sure builder.sh is chmod a+x
            builder_st = os.stat(script_dst)
            os.chmod(script_dst, builder_st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            # make /app/vendor
            slash_app = os.path.join(get_container_path(buildproc), 'app')
            mkdir(os.path.join(slash_app, 'vendor'))
            chowntree(slash_app, username=user)
            subprocess.check_call([runner, runner_cmd, 'buildproc.yaml'])
        finally:
            subprocess.check_call([runner, 'teardown', 'buildproc.yaml'])

        with lock_or_wait(cachefolder):
            shutil.rmtree(cachefolder, ignore_errors=True)
            os.rename('cache', cachefolder)

        if make_tarball:
            build_data.release_data = recover_release_data(app_folder)

            bp = recover_buildpack(app_folder)
            build_data.buildpack_url = bp.url + '#' + bp.version
            build_data.buildpack_version = bp.version

            # slugignore
            clean_slug_dir(app_folder)

            # tar up the result
            with tarfile.open('build.tar.gz', 'w:gz') as tar:
                tar.add(app_folder, arcname='')
            build_data.build_md5 = file_md5('build.tar.gz')

            tardest = os.path.join(outfolder, 'build.tar.gz')
            os.rename('build.tar.gz', tardest)

            build_data_path = os.path.join(outfolder, 'build_result.yaml')
            print "Writing", build_data_path
            with open(build_data_path, 'wb') as f:
                f.write(build_data.as_yaml())


def recover_release_data(app_folder):
    """
    Given the path to an app folder where an app was just built, return a
    dictionary containing the data emitted from running the buildpack's release
    script.

    Relies on the builder.sh script storing the release data in ./.release.yaml
    inside the app folder.
    """
    with open(os.path.join(app_folder, '.release.yaml'), 'rb') as f:
        return yaml.safe_load(f)


def recover_buildpack(app_folder):
    """
    Given the path to an app folder where an app was just built, return a
    BuildPack object pointing to the dir for the buildpack used during the
    build.

    Relies on the builder.sh script storing the buildpack location in
    /.buildpack inside the container.
    """
    filepath = os.path.join(app_folder, '.buildpack')
    with open(filepath, 'rb') as f:
        buildpack_picked = f.read()
    buildpack_picked = buildpack_picked.lstrip('/')
    buildpack_picked = buildpack_picked.rstrip('\n')
    buildpack_picked = os.path.join(os.getcwd(), buildpack_picked)
    return BuildPack(buildpack_picked)


def pull_app(name, url, version, vcs_type):
    just_url = url.partition('#')[0]
    with lock_or_wait(just_url):
        app = update_app(name, url, version, vcs_type=vcs_type)
        dest = name + '-' + hashlib.md5(just_url).hexdigest()
        shutil.copytree(app.folder, dest)
    return dest


def pull_buildpack(url):
    """
    Update a buildpack in its shared location, then make a copy into the
    current directory, using an md5 of the url.
    """
    just_url = url.partition('#')[0]
    with lock_or_wait(just_url):
        bp = update_buildpack(url)
        dest = bp.basename + '-' + hashlib.md5(just_url).hexdigest()
        shutil.copytree(bp.folder, dest)
    return dest


def pull_buildpacks(urls):
    return [pull_buildpack(u) for u in urls]
