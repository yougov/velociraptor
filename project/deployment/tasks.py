import logging
import tempfile
import os
import shutil
import posixpath
import datetime
import contextlib

import fabric.network
from celery.task import subtask, task as celery_task
from fabric.api import env
from django.core.files.storage import default_storage
import yaml

from deployment.models import Release, App, Build, Swarm
from yg.deploy.fabric.system import deploy_parcel, delete_proc as fab_delete_proc
from yg.deploy.paver import build as paver_build


class tmpdir(object):
    """Context processor for putting you into a temporary directory on enter
    and deleting the directory on exit
    """
    def __init__(self):
        self.orig_path = os.getcwd()

    def __enter__(self):
        self.temp_path = tempfile.mkdtemp()
        os.chdir(self.temp_path)

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)
        shutil.rmtree(self.temp_path, ignore_errors=True)


@celery_task()
def deploy(release_id, profile, host, proc, port, user, password, callback=None):
    release = Release.objects.get(id=release_id)

    # Set up env for Fabric
    env.host_string = host
    env.abort_on_prompts = True
    env.celery_task = deploy
    env.user=user
    env.password=password

    deploy.update_state(state='PROGRESS', meta='Started')
    logging.info('%s deploying %s:%s to %s:%s' % (user, release, proc, host, port))

    with tmpdir():
        f = open('settings.yaml', 'wb')
        f.write(release.config)
        f.close()
        # pull the build out of gridfs, write it to a temporary location, and
        # deploy it.
        build_name = posixpath.basename(release.build.file.name)
        local_build = open(build_name, 'wb')
        build = default_storage.open(release.build.file.name)
        local_build.write(build.read())

        local_build.close()
        build.close()

        with always_disconnect():
            result = deploy_parcel(build_name, 'settings.yaml', profile,
                proc, port)

    # start callback if there is one.
    if callback is not None:
        subtask(callback).delay()

    return result


@celery_task()
def build_hg(app_id, tag, callback=None):
    # call the assemble_hg function.
    app = App.objects.get(id=app_id)
    url = '%s#%s' % (app.repo_url, tag)
    with tmpdir():
        build = Build(app=app, tag=tag, start_time=datetime.datetime.now(),
                      status='started')
        build.save()

        try:
            build_path = paver_build.assemble_hg_raw(url)
            # Save the file to Mongo GridFS
            localfile = open(build_path, 'r')
            name = posixpath.basename(build_path)
            filepath = 'builds/' + name
            default_storage.save(filepath, localfile)
            localfile.close()
            build.file = filepath
            build.end_time = datetime.datetime.now()
            build.status = 'success'
        except:
            build.status = 'failed'

        build.save()

    # start callback if there is one.
    if callback is not None:
        subtask(callback).delay()


@celery_task()
def delete_proc(host, proc, user, password):
    env.host_string = host
    env.abort_on_prompts = True
    env.user=user
    env.password=password
    logging.info('%s deleting %s on %s' % (user, proc, host))
    with always_disconnect():
        fab_delete_proc(proc)


def _new_release(profile, build):
    new = Release(
        profile=profile,
        build=build,
        config=profile.to_yaml(),
    )
    new.hash = new.compute_hash()
    new.save()


def _get_current_release(profile, build):
    # If there's a release with app, tag, and profile's current config,
    # then return it.  Else make one.
    releases = Release.objects.filter(profile=profile,
                                      build__app=build.app,
                                      build__tag=build.tag).order_by('-id')

    if not releases:
        return _new_release(profile, build)

    # There's at least one release for this profile/app/tag.  See if
    # its config is current.  Make new release if not.
    latest = releases[0]
    current_config = profile.assemble()
    last_config = yaml.safe_load(latest.config)
    if current_config == last_config:
        return latest
    else:
        return _new_release(profile, build)


@celery_task()
def unleash_swarm(swarm_id, user, password):
    swarm = Swarm.objects.get(id=swarm_id)
    callback = unleash_swarm.subtask((swarm.id,))

    # is there a build for this app and tag?  If not, build it.
    try:
        build = Build.objects.get(app=swarm.app, tag=swarm.tag,
                                  status='success', file__isnull=False)
    except Build.DoesNotExist:
        # TODO: once there's a django-celery version that works with celery2.6,
        # switch to the new-style callbacks using the 'link' argument to
        # apply_async
        build_hg.delay(swarm.app.id, swarm.tag, callback)

    # we have a build!
    # Now see if we have a release that uses our build and 
    if swarm.release is None:
        # for unleash_swarm to work, the swarm must have either:
            # - a swarm.release, for cases when a brand new swarm is being
            # created
            # - or a swarm.replaces, for cases when an existing swarm is being
            # replaced by one with new config, build, or size
        # If we get to this point, we must be in the second situation, or a
        # failure mode.
        if swarm.replaces is None or swarm.replaces.release is None:
            raise Exception("Swarm %s has neither a 'release' nor a "
                            "'replaces' release" % swarm_id)

        profile = swarm.replaces.release.profile
        swarm.release = _get_current_release(profile, build)
        swarm.save()

    # OK we have a release.  Next: see if we need to do a deployment.
    # Query squad for list of procs.
    if len(swarm.get_procs() < swarm.size):
        # get next target host
        host = swarm.get_next_host()
        port = host.get_next_port()
        # deploy new proc to host, and set this function as callback.
        deploy.delay(swarm.release.id, swarm.release.profile.name, host,
                     swarm.proc_name, port, user, password, callback=callback)


    logging.info("IT IS FINISHED")


@contextlib.contextmanager
def always_disconnect():
    """
    to address #18366, disconnect every time.
    """
    try:
        yield
    finally:
        fabric.network.disconnect_all()
