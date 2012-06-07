import logging
import tempfile
import os
import shutil
import posixpath
import datetime
import contextlib
import re
from collections import defaultdict

import fabric.network
from celery.task import subtask, chord, task
from fabric.api import env
from django.core.files.storage import default_storage

from deployment.models import Release, Build, Swarm, Host, PortLock
from deployment import balancer

from yg.deploy.fabric.system import (deploy_parcel, run_uptests, delete_proc as
                                     fab_delete_proc)
from yg.deploy.paver import build as paver_build


class tmpdir(object):
    """Context manager for putting you into a temporary directory on enter
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


class remove_port_lock(object):
    """
    Context manager for removing a port lock on a host.  Requires a hostname
    and port on init.
    """

    # This used just during deployment.  In general the host itself is the
    # source of truth about what ports are in use. But when deployments are
    # still in flight, port locks are necessary to prevent collisions.

    def __init__(self, hostname, port):
        self.host = Host.objects.get(name=hostname)
        self.port = int(port)

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        try:
            self.lock = PortLock.objects.get(host=self.host, port=self.port)
            self.lock.delete()
        except PortLock.DoesNotExist:
            pass


@task
def deploy(release_id, profile_name, hostname, proc, port, user, password):

    with remove_port_lock(hostname, port):
        release = Release.objects.get(id=release_id)

        assert release.build.file, "Build %s has no file" % release.build
        assert release.hash, "Release %s has not been hashed" % release

        # Set up env for Fabric
        env.host_string = hostname
        env.abort_on_prompts = True
        env.task = deploy
        env.user=user
        env.password=password

        deploy.update_state(state='PROGRESS', meta='Started')
        logging.info('%s deploying %s:%s to %s:%s' % (user, release, proc,
                                                      hostname, port))

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


@task
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

            # the name that comes out will start with whatever the last
            # component in the hg repo url is.  We'd rather use the app name.
            name = re.sub('^[^-]*', app.name, name)
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


@task
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


@task
def swarm_start(swarm_id, user, password):
    """
    Given a swarm_id, username, and password, kick off the chain of tasks
    necessary to get this swarm deployed.
    """
    swarm = Swarm.objects.get(id=swarm_id)

    # is there a build for this app and tag?  If so, call next step.  If not,
    # build it, then call next step.
    build = swarm.release.build
    if build.file.name:
        swarm_release.delay(swarm_id, user, password)
    else:
        callback = swarm_release.subtask((swarm.id, user, password))
        build_hg.delay(build.id, callback)


# This task should only be used as a callback after swarm_start
@task
def swarm_release(swarm_id, user, password):
    """
    Assuming the swarm's build is complete, this task will ensure there's a
    release with that build + current config, and call subtasks to make sure
    there are enough deployments.
    """
    swarm = Swarm.objects.get(id=swarm_id)
    build = swarm.release.build

    # Bail out if the build doesn't have a file
    assert build.file, "Build %s has no file" % build

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
    all_procs = swarm.all_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]

    procs_needed = swarm.size - len(current_procs)

    # set uptest task as chord callback
    callback = swarm_post_deploy.subtask((swarm.id, user, password))

    if procs_needed > 0:
        hosts = swarm.get_prioritized_hosts()
        hostcount = len(hosts)

        # Build up a dictionary where the keys are hostnames, and the
        # values are lists of ports.
        new_procs_by_host = defaultdict(list)
        for x in xrange(procs_needed):
            host = hosts[x % hostcount]
            port = host.get_next_port()
            new_procs_by_host[host.name].append(port)

            # Ports need to be locked here in the synchronous loop, before
            # fanning out the async subtasks, in order to prevent collisions.
            pl = PortLock(host=host, port=port)
            pl.save()

        # Now loop over the hosts and fan out a task to each that needs it.
        subtasks = []
        for host in hosts:
            if host.name in new_procs_by_host:
                subtasks.append(
                    swarm_deploy_to_host.subtask((
                        swarm.id,
                        host.id,
                        new_procs_by_host[host.name],
                        user,
                        password,
                    ))
                )
        chord(subtasks)(callback)
    elif procs_needed < 0:
        # We need to delete some procs

        # reverse prioritized list so the most loaded hosts get things removed
        # first.
        hosts = swarm.get_prioritized_hosts()
        hosts.reverse()
        hostcount = len(hosts)
        subtasks = []
        for x in xrange(procs_needed * -1):
            host = hosts[x % hostcount]
            proc = host.swarm_procs.pop()
            subtasks.append(
                swarm_delete_proc.subtask((
                    swarm.id, host.name, proc.name, proc.port, user, password,
                ))
            )
        chord(subtasks)(callback)
    else:
        # We have just the right number of procs.  Uptest and route them.
        swarm_assign_uptests(swarm.id, user, password)


@task
def swarm_deploy_to_host(swarm_id, host_id, ports, user, password):
    """
    Given a swarm, a host, and a list of ports, deploy the swarm's current
    release to the host, one instance for each port.
    """
    # This function allows a swarm's deployments to be parallel across
    # different hosts, but synchronous on a per-host basis, which solves the
    # problem of two deployments both trying to copy the release over at the
    # same time.

    swarm = Swarm.objects.get(id=swarm_id)
    host = Host.objects.get(id=host_id)
    for port in ports:
        deploy(
            swarm.release.id,
            swarm.release.profile.name,
            host.name,
            swarm.proc_name,
            port,
            user,
            password,
        )

    procnames = ["%s-%s-%s" % (swarm.release, swarm.proc_name, port) for port
                 in ports]

    return host.name, procnames


@task
def swarm_post_deploy(deploy_results, swarm_id, user, password):
    """
    Chord callback run after deployments.  Should check for exceptions, then
    launch uptests.
    """
    if any(isinstance(r, Exception) for r in deploy_results):
        assert False, "Error in deployment."

    swarm_assign_uptests(swarm_id, user, password)


@task
def swarm_assign_uptests(swarm_id, user, password):
    swarm = Swarm.objects.get(id=swarm_id)
    all_procs = swarm.all_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]

    # Organize procs by host
    host_procs = defaultdict(list)
    for proc in current_procs:
        host_procs[proc.host.name].append(proc.name)


    subtasks = []
    for hostname, procs in host_procs.items():

        subtasks.append(
            swarm_uptest_host.subtask((
                hostname,
                procs,
                user,
                password,
            ))
        )

    callback = swarm_post_uptest.subtask((swarm_id, user, password))
    chord(subtasks)(callback)


@task
def swarm_uptest_host(hostname, procs, user, password):
    # Do uptests for each proc on host.
    env.host_string = hostname
    env.abort_on_prompts = True
    env.user=user
    env.password=password
    for proc in procs:
        run_uptests(proc)

    return hostname, procs


@task
def swarm_post_uptest(uptest_results, swarm_id, user, password):
    """
    Chord callback that runs after uptests have completed.  Checks that they
    were successful, and then calls routing function.
    """

    if any(isinstance(r, Exception) for r in uptest_results):
        assert False, "Error in uptests."

    procnames_by_host = uptest_results
    correct_nodes = set()
    for host, procnames in uptest_results:
        for procname in procnames:
            correct_nodes.add('%s:%s' % (host, procname.split('-')[-1]))

    callback = swarm_cleanup.subtask((swarm_id, user, password))
    swarm_route(swarm_id, list(correct_nodes), user, password, callback)


@task
def swarm_route(swarm_id, correct_nodes, user, password, callback=None):
    """
    Given a list of nodes for the current swarm, make sure those nodes and
    only those nodes are in the swarm's routing pool, if it has one.
    """
    # It's important that the node list be passed to this function from the
    # uptest finisher, rather than having this function build that list itself,
    # because if it built the list itself it couldn't be sure that all the
    # nodes had been uptested.  It's possible that one could have crept in
    # throuh a non-swarm deployment, for example.

    swarm = Swarm.objects.get(id=swarm_id)
    all_procs = swarm.all_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]
    stale_procs = [p for p in all_procs if p.hash != swarm.release.hash]
    if swarm.pool:
        # There's just the right number of procs.  Make sure the balancer is up
        # to date, but only if the swarm has a pool specified.


        current_nodes = set(balancer.get_nodes(swarm.squad.balancer,
                                               swarm.pool))

        correct_nodes = set(correct_nodes)

        new_nodes = correct_nodes.difference(current_nodes)

        stale_nodes = current_nodes.intersection(p.as_node() for p in
                                                      stale_procs)

        if new_nodes:
            balancer.add_nodes(swarm.squad.balancer, swarm.pool,
                               list(new_nodes))

        if stale_nodes:
            balancer.delete_nodes(swarm.squad.balancer, swarm.pool,
                                  list(stale_nodes))

    if callback is not None:
        subtask(callback).delay()


@task
def swarm_cleanup(swarm_id, user, password):
    """
    Delete any procs in the swarm that aren't from the current release.
    """
    swarm = Swarm.objects.get(id=swarm_id)
    all_procs = swarm.all_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]
    stale_procs = [p for p in all_procs if p.hash != swarm.release.hash]

    # Only delete old procs if the deploy of the new ones was successful.
    if stale_procs and len(current_procs) >= swarm.size:
        for p in stale_procs:
            delete_proc.delay(p.host.name, p.name, user, password)


@task
def swarm_delete_proc(swarm_id, hostname, procname, port, user, password):
    # wrap the regular delete_proc, but first ensure the proc is removed from
    # the routing pool.  This is done on a per-proc basis because sometimes
    # it's called when deleting old procs, and other times it's called when we
    # just have too many of the current proc.  If it handles its own routing,
    # this function can be used in both places.
    swarm = Swarm.objects.get(id=swarm_id)
    if swarm.pool:
        node = '%s:%s' % (hostname, port)
        if node in balancer.get_nodes(swarm.squad.balancer, swarm.pool):
            balancer.delete_nodes(swarm.squad.balancer, swarm.pool, [node])

    delete_proc(hostname, procname, user, password)


@contextlib.contextmanager
def always_disconnect():
    """
    to address #18366, disconnect every time.
    """
    try:
        yield
    finally:
        fabric.network.disconnect_all()
