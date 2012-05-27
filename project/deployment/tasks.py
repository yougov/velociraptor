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

from deployment.models import Release, Build, Swarm
from deployment import balancer

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
def deploy(release_id, profile_name, host, proc, port, user, password, callback=None):
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
            result = deploy_parcel(build_name, 'settings.yaml', profile_name,
                proc, port, 'nobody', release.hash)

    # start callback if there is one.
    if callback is not None:
        subtask(callback).delay()

    return result


@celery_task()
def build_hg(build_id, callback=None):
    # call the assemble_hg function.
    build = Build.objects.get(id=build_id)
    app = build.app
    url = '%s#%s' % (build.app.repo_url, build.tag)
    with tmpdir():
        build.status = 'started'
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
def delete_proc(host, proc, user, password, callback=None):
    env.host_string = host
    env.abort_on_prompts = True
    env.user=user
    env.password=password
    logging.info('%s deleting %s on %s' % (user, proc, host))
    with always_disconnect():
        fab_delete_proc(proc)

    if callback:
        subtask(callback).delay()


@celery_task()
def unleash_swarm(swarm_id, user, password):
    swarm = Swarm.objects.get(id=swarm_id)

    callback = unleash_swarm.subtask((swarm.id, user, password))

    # is there a build for this app and tag?  If not, build it.
    build = swarm.release.build
    if not build.file.name:
        build_hg.delay(build.id, callback)
        return

    # IF the release hasn't been frozen yet, then it was probably waiting on a
    # build being done.  Freeze it now.
    if not swarm.release.hash:
        # Release has not been frozen yet, probably because we were waiting on
        # the build.  Since there's a build file now, saving will force the
        # release to hash itself. 
        release = swarm.release
        release.config = swarm.profile.to_yaml()
        release.save()
    elif swarm.release.parsed_config() != swarm.profile.assemble():
        # Our frozen release doesn't have current config.  We'll need to make a
        # new release, with the same build, and link the swarm to that.
        release = Release(profile=swarm.profile, build=build,
                          config=swarm.profile.to_yaml())
        release.save()
        swarm.release = release
        swarm.save()


    # OK we have a release.  Next: see if we need to do a deployment.
    # Query squad for list of procs.
    # TODO: Allow this deployment step to execute in parallel instead of
    # only serially.  Idea: For each host record, save a list of the procs it's
    # supposed to be running.  Then just have this function check supervisord's
    # list against that list, and create all the new procs that are necessary.
    all_procs = swarm.all_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]
    stale_procs = [p for p in all_procs if p.hash != swarm.release.hash]

    if len(current_procs) < swarm.size:
        # get next target host
        host = swarm.get_next_host()
        port = host.get_next_port()
        # deploy new proc to host, and set this function as callback.
        deploy.delay(swarm.release.id, swarm.release.profile.name, host.name,
                     swarm.proc_name, port, user, password, callback)
        return
    elif len(current_procs) > swarm.size:
        # We have too many procs in the swarm.  Delete one and call back.
        # TODO: instead of just deleting the first proc in the list, delete one
        # 1) from the host with the most procs from this swarm on it, or 2) if
        # there's a tie, from the host with the most procs on it of any type.
        p = current_procs[0]
        delete_proc.delay(p.host.name, p.name, user, password, callback)
        return
    elif swarm.pool:
        # There's just the right number of procs.  Make sure the balancer is up
        # to date, but only if the swarm has a pool specified.

        # TODO: run uptests on new nodes before routing them.

        current_nodes = set(balancer.get_nodes(swarm.squad.balancer,
                                               swarm.pool))

        correct_nodes = set(p.as_node() for p in current_procs)

        new_nodes = correct_nodes.difference(current_nodes)

        stale_nodes = current_nodes.intersection(p.as_node() for p in
                                                      stale_procs)

        if new_nodes:
            balancer.add_nodes(swarm.squad.balancer, swarm.pool,
                               list(new_nodes))

        if stale_nodes:
            balancer.delete_nodes(swarm.squad.balancer, swarm.pool,
                                  list(stale_nodes))


    # If there are live procs from our profile using something other than the
    # current release, they should be deleted.
    if len(stale_procs):
        # destroy the first stale proc, and call back
        p = stale_procs[0]
        delete_proc.delay(p.host.name, p.name, user, password, callback)
        return

    logging.info(u"Swarm unleashed: %s" % swarm)


@contextlib.contextmanager
def always_disconnect():
    """
    to address #18366, disconnect every time.
    """
    try:
        yield
    finally:
        fabric.network.disconnect_all()
