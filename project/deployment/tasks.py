import logging
import tempfile
import os
import shutil
import posixpath
import datetime
import contextlib
import re
import traceback
import functools
from collections import defaultdict

import envoy
import yaml
import fabric.network
import redis
from celery.task import subtask, chord, task
from fabric.api import env
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone

from deployment.models import (Release, Build, Swarm, Host, PortLock, App,
                               TestRun, TestResult)
from deployment import models
from deployment import balancer, events, utils
from raptor import repo, remote, build as rbuild
from raptor.models import Proc
from raptor.utils import tmpdir


logger = logging.getLogger('velociraptor')

def send_event(title, msg, tags=None):
    logging.info(msg)
    # Create and discard connections when needed.  More robust than trying to
    # hold them open for a long time.
    sender = events.EventSender(
        settings.EVENTS_PUBSUB_URL,
        settings.EVENTS_PUBSUB_CHANNEL,
        settings.EVENTS_BUFFER_KEY,
        settings.EVENTS_BUFFER_LENGTH,
    )
    sender.publish(msg, title=title, tags=tags)
    sender.close()


class event_on_exception(object):
    """
    Decorator that puts a message on the pubsub for any exception raised in the
    decorated function.
    """
    def __init__(self, tags=None):
        self.tags = tags or []
        self.tags.append('failed')

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except (Exception, SystemExit) as e:
                try:
                    send_event(title=str(e), msg=traceback.format_exc(),
                               tags=self.tags)
                finally:
                    raise
        return wrapper


@task
@event_on_exception(['deploy'])
def deploy(release_id, recipe_name, hostname, proc, port, contain=False):
    with remove_port_lock(hostname, port):
        release = Release.objects.get(id=release_id)
        msg_title = '%s-%s-%s' % (release.build.app.name, release.build.tag, proc)
        logging.info('beginning deploy of %s-%s-%s to %s' % (release, proc,
                                                             port,
                                                             hostname))
        send_event(title=msg_title, msg='deploying %s-%s-%s to %s' %
              (release, proc, port, hostname), tags=['deploy'])

        assert release.build.file, "Build %s has no file" % release.build
        assert release.hash, "Release %s has not been hashed" % release

        # Set up env for Fabric
        env.host_string = hostname
        env.abort_on_prompts = True
        env.task = deploy
        env.user = settings.DEPLOY_USER
        env.password = settings.DEPLOY_PASSWORD
        env.linewise = True

        with tmpdir():
            # write the settings.yaml locally
            with open('settings.yaml', 'wb') as f:
                f.write(release.config)

            # write the env.sh locally
            with open('env.sh', 'wb') as f:
                def format_var(key, val):
                    return '%(key)s="%(val)s"' % vars()
                e = release.env_vars or {}
                env_str = '\n'.join(format_var(k, e[k]) for k in e)
                f.write(env_str)

            # pull the build out of gridfs, write it to a temporary location,
            # and deploy it.
            build_filename = posixpath.basename(release.build.file.name)
            local_build = open(build_filename, 'wb')
            build = default_storage.open(release.build.file.name)
            local_build.write(release.build.file.read())

            local_build.close()
            build.close()

            with always_disconnect():
                remote.deploy_parcel(
                              build_path=build_filename,
                              config_path='settings.yaml',
                              envsh_path='env.sh',
                              recipe=recipe_name,
                              proc=proc,
                              release_hash=release.hash,
                              port=port,
                              user=getattr(settings, 'PROC_USER', 'nobody'),
                              use_syslog=getattr(settings, 'PROC_SYSLOG',
                                                 False),
                              contain=contain)



class CmdError(Exception):
    """
    Exception subclass for when we shell out to the cmd line with envoy and the
    cmd fails.
    """
    def __init__(self, envoy_result, *args, **kwargs):
        msg = ("'%(command)s' returned code %(status_code)s. \n"
               "stdout: %(std_out)s\n"
               "stderr: %(std_err)s") % envoy_result.__dict__
        super(CmdError, self).__init__(msg, *args, **kwargs)


def run(cmd):
    """
    Wrap envoy.run to raise helpful exception if a command doesn't exit with
    status 0.
    """
    result = envoy.run(cmd)
    if result.status_code == 0:
        return result
    else:
        raise CmdError(result)


@task
@event_on_exception(['build'])
def build_app(build_id, callback=None):
    build = Build.objects.get(id=build_id)
    send_event(str(build), "Started build %s" % build, tags=['build'])
    app = build.app
    # remember when we started building
    build.status = 'started'
    build.start_time = timezone.now()
    build.save()
    try:
        with tmpdir() as here:
            # Check out project and update to specified version
            app_path = os.path.join(here, repo.basename(app.repo_url))
            repo_kwargs = {
                'folder': app_path,
                'url': app.repo_url,
                'vcs_type': app.repo_type,
            }

            # If the app specifies a buildpack, just use that.  Else make sure
            # all buildpacks are cloned and specify the order in which they
            # should be checked against the repo.
            if app.buildpack:
                repo_kwargs['buildpack'] = app.buildpack.get_repo()
            else:
                for bp in models.BuildPack.objects.all():
                    bp.get_repo()
                repo_kwargs['buildpack_order'] = models.BuildPack.get_order()

            app_repo = rbuild.App(**repo_kwargs)
            app_repo.update(build.tag)
            app_repo.compile()
            # tar the build
            name_tmpl = '%(app)s-%(version)s-%(time)s.tar.bz2'
            time = timezone.now()
            name = name_tmpl % {'app': build.app,
                                'version': build.tag,
                                'time': time.strftime('%Y-%m-%dT%H-%M')}

            tar_params = {'filename': name, 'folder': app_repo.folder}
            run('tar -C %(folder)s -cjf %(filename)s .' % tar_params)
            filepath = 'builds/' + name
            with open(name, 'rb') as localfile:
                default_storage.save(filepath, localfile)

            # XXX DEBUG.  Also write a copy locally so we can test untarring
            envoy.run('cp %s /tmp/build.tar.bz2' % name)

            build.file = filepath
            build.end_time = time
            build.status = 'success'
            build.env_vars = app_repo.release().get('config_vars')
            build.buildpack_url = app_repo.buildpack.url
            build.buildpack_version = app_repo.buildpack.version
    except:
        build.status = 'failed'
        raise
    finally:
        build.save()

    send_event(str(build), "Completed build %s" % build, tags=['build',
                                                               'success'])

    # start callback if there is one.
    if callback is not None:
        subtask(callback).delay()

    # If there were any other swarms waiting on this build, kick them off
    build_start_waiting_swarms(build.id)


@task
def update_tags():
    env.linewise = True
    for app in App.objects.filter(repo_url__isnull=False):
        if app.repo_url:
            tags = paver_build.get_latest_tags(app.repo_url, app.id)
            tags = tags.split()
            app.tag_set.all().delete()
            for tag in tags:
                app.tag_set.create(name=tag)


@task
@event_on_exception(['proc', 'deleted'])
def delete_proc(host, proc, callback=None):
    env.host_string = host
    env.abort_on_prompts = True
    env.user = settings.DEPLOY_USER
    env.password = settings.DEPLOY_PASSWORD
    env.linewise = True
    with always_disconnect():
        remote.delete_proc(proc)
    send_event(Proc.name_to_shortname(proc), 'deleted %s on %s' % (proc, host), tags=['proc', 'deleted'])

    if callback:
        subtask(callback).delay()


def swarm_wait_for_build(swarm, build):
    """
    Given a swarm that you want to have swarmed ASAP, and a build that the
    swarm is waiting to finish, push the swarm's ID onto the build's waiting
    list.
    """
    msg = 'Swarm %s waiting for completion of build %s' % (swarm, build)
    send_event('%s waiting' % swarm, msg, ['wait'])
    with tmpredis() as r:
        key = getattr(settings, 'BUILD_WAIT_PREFIX', 'buildwait_') + str(build.id)
        r.lpush(key, swarm.id)
        r.expire(key, getattr(settings, 'BUILD_WAIT_AGE', 3600))


def build_start_waiting_swarms(build_id):
    with tmpredis() as r:
        key = getattr(settings, 'BUILD_WAIT_PREFIX', 'buildwait_') + str(build_id)
        swarm_id = r.lpop(key)
        while swarm_id:
            swarm_start.delay(swarm_id)
            swarm_id = r.lpop(key)


@task
def swarm_start(swarm_id):
    """
    Given a swarm_id, kick off the chain of tasks necessary to get this swarm
    deployed.
    """
    swarm = Swarm.objects.get(id=swarm_id)
    build = swarm.release.build

    if build.is_usable():
        # Build is good.  Do a release.
        swarm_release.delay(swarm_id)
    elif build.in_progress():
        # Another swarm call already started a build for this app/tag.  Instead
        # of starting a duplicate, just push the swarm ID onto the build's
        # waiting list.
        swarm_wait_for_build(swarm, build)
    else:
        callback = swarm_release.subtask((swarm.id,))
        build_app.delay(build.id, callback)


# This task should only be used as a callback after swarm_start
@task
def swarm_release(swarm_id):
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
        release.config = swarm.recipe.to_yaml()
        release.save()
    elif swarm.release.parsed_config() != swarm.recipe.assemble():
        # Our frozen release doesn't have current config.  We'll need to make a
        # new release, with the same build, and link the swarm to that.
        swarm.release = swarm.recipe.get_current_release(build.tag)
        swarm.save()

    # OK we have a release.  Next: see if we need to do a deployment.
    # Query squad for list of procs.
    all_procs = swarm.get_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]

    procs_needed = swarm.size - len(current_procs)

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
                    ))
                )
        callback = swarm_post_deploy.subtask((swarm.id,))
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
                swarm_delete_proc.subtask((swarm.id, host.name, proc.name,
                                           proc.port))
            )
        callback = swarm_post_deploy.subtask((swarm.id,))
        chord(subtasks)(callback)
    else:
        # We have just the right number of procs.  Uptest and route them.
        swarm_assign_uptests(swarm.id)


@task
def swarm_deploy_to_host(swarm_id, host_id, ports):
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
            swarm.release.recipe.name,
            host.name,
            swarm.proc_name,
            port,
            contain=True,
        )

    procnames = ["%s-%s-%s" % (swarm.release, swarm.proc_name, port) for port
                 in ports]

    return host.name, procnames


@task
def swarm_post_deploy(deploy_results, swarm_id):
    """
    Chord callback run after deployments.  Should check for exceptions, then
    launch uptests.
    """
    if any(isinstance(r, Exception) for r in deploy_results):
        swarm = Swarm.objects.get(id=swarm_id)
        msg = "Error in deployments for swarm %s" % swarm
        send_event('Swarm %s aborted' % swarm, msg, tags=['failed'])
        raise Exception(msg)

    swarm_assign_uptests(swarm_id)


@task
def swarm_assign_uptests(swarm_id):
    swarm = Swarm.objects.get(id=swarm_id)
    all_procs = swarm.get_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]

    # Organize procs by host
    host_procs = defaultdict(list)
    for proc in current_procs:
        host_procs[proc.host.name].append(proc.name)

    header = [uptest_host_procs.subtask((h, ps)) for h, ps in
              host_procs.items()]

    this_chord = chord(header)
    callback = swarm_post_uptest.s(swarm_id)
    this_chord(callback)


@task
def uptest_host_procs(hostname, procs):
    env.host_string = hostname
    env.abort_on_prompts = True
    env.user = settings.DEPLOY_USER
    env.password = settings.DEPLOY_PASSWORD
    env.linewise = True

    with always_disconnect():
        results = {p: remote.run_uptests(p) for p in procs}
    return hostname, results


@task
def uptest_host(hostname, test_run_id=None):
    """
    Given a hostname, look up all its procs and then run uptests on them.
    """

    host = Host.objects.get(name=hostname)
    procs = host.get_procs()
    _, results = uptest_host_procs(hostname, [p.name for p in procs])

    if test_run_id:
        run = TestRun.objects.get(id=test_run_id)
        for procname, resultlist in results.items():
            testcount = len(resultlist)
            if testcount:
                passed = all(r['Passed'] for r in resultlist)
            else:
                # There were no tests :(
                passed = True

            tr = TestResult(
                run=run,
                time=timezone.now(),
                hostname=hostname,
                procname=procname,
                passed=passed,
                testcount=testcount,
                results=yaml.safe_dump(resultlist)
            )
            tr.save()
    return hostname, results


class FailedUptest(Exception):
    pass


@task
def swarm_post_uptest(uptest_results, swarm_id):
    """
    Chord callback that runs after uptests have completed.  Checks that they
    were successful, and then calls routing function.
    """

    # uptest_results will be a list of tuples in form (host, results), where
    # 'results' is a list of dictionaries, one for each test script.

    swarm = Swarm.objects.get(id=swarm_id)
    test_counter = 0
    for host_results in uptest_results:
        if isinstance(host_results, Exception):
            raise host_results
        host, proc_results = host_results
         #results is now a dict
        for proc, results in proc_results.items():
            for result in results:
                test_counter += 1
                # This checking/formatting relies on each uptest result being a
                # dict with 'Passed', 'Name', and 'Output' keys.
                if result['Passed'] != True:
                    msg = (proc + ": {Name} failed:"
                           "{Output}".format(**result))
                    send_event(str(swarm), msg, tags=['failed', 'uptest'])
                    raise FailedUptest(msg)

    # Don't congratulate swarms that don't actually have any uptests.
    if test_counter > 0:
        send_event("Uptests passed", 'Uptests passed for swarm %s' % swarm,
                   tags=['success', 'uptest'])
    else:
        send_event("No uptests!", 'No uptests for swarm %s' % swarm,
                   tags=['warning', 'uptest'])

    # Also check for captured failures in the results
    correct_nodes = set()
    for host, results in uptest_results:
        # results is now a dictionary keyed by procname
        for procname in results:
            correct_nodes.add('%s:%s' % (host, procname.split('-')[-1]))

    callback = swarm_cleanup.subtask((swarm_id,))
    swarm_route.delay(swarm_id, list(correct_nodes), callback)


@task
@event_on_exception(['route'])
def swarm_route(swarm_id, correct_nodes, callback=None):
    """
    Given a list of nodes for the current swarm, make sure those nodes and
    only those nodes are in the swarm's routing pool, if it has one.
    """
    # It's important that the correct_nodes list be passed to this function
    # from the uptest finisher, rather than having this function build that
    # list itself, because if it built the list itself it couldn't be sure that
    # all the nodes had been uptested.  It's possible that one could have crept
    # in throuh a non-swarm deployment, for example.

    swarm = Swarm.objects.get(id=swarm_id)
    if swarm.pool:
        # There's just the right number of procs.  Make sure the balancer is up
        # to date, but only if the swarm has a pool specified.

        current_nodes = set(balancer.get_nodes(swarm.balancer, swarm.pool))

        correct_nodes = set(correct_nodes)

        new_nodes = correct_nodes.difference(current_nodes)

        stale_nodes = current_nodes.difference(correct_nodes)

        if new_nodes:
            balancer.add_nodes(swarm.balancer, swarm.pool,
                               list(new_nodes))

        if stale_nodes:
            balancer.delete_nodes(swarm.balancer, swarm.pool,
                                  list(stale_nodes))
        send_event(str(swarm), 'Routed swarm %s.  New nodes: %s' % (swarm, list(correct_nodes)),
             tags=['route'])

    if callback is not None:
        subtask(callback).delay()


@task
def swarm_cleanup(swarm_id):
    """
    Delete any procs in the swarm that aren't from the current release.
    """
    swarm = Swarm.objects.get(id=swarm_id)
    all_procs = swarm.get_procs()
    current_procs = [p for p in all_procs if p.hash == swarm.release.hash]
    stale_procs = [p for p in all_procs if p.hash != swarm.release.hash]

    # Only delete old procs if the deploy of the new ones was successful.
    if stale_procs and len(current_procs) >= swarm.size:
        for p in stale_procs:
            # We don't need to worry about removing these nodes from a pool at
            # this point, so just call delete_proc instead of swarm_delete_proc
            delete_proc.delay(p.host.name, p.name)


@task
def swarm_delete_proc(swarm_id, hostname, procname, port):
    # wrap the regular delete_proc, but first ensure the proc is removed from
    # the routing pool.  This is done on a per-proc basis because sometimes
    # it's called when deleting old procs, and other times it's called when we
    # just have too many of the current proc.  If it handles its own routing,
    # this function can be used in both places.
    swarm = Swarm.objects.get(id=swarm_id)
    if swarm.pool:
        node = '%s:%s' % (hostname, port)
        if node in balancer.get_nodes(swarm.balancer, swarm.pool):
            balancer.delete_nodes(swarm.balancer, swarm.pool, [node])

    delete_proc(hostname, procname)


@task
def uptest_all_procs():
    # Create a test run record.
    run = TestRun(start=timezone.now())
    run.save()
    # Fan out a task for each active host
    # callback post_uptest_all_procs at the end
    hosts = Host.objects.filter(active=True)

    def make_test_task(host):
        return uptest_host.subtask((host.name, run.id), expires=120)
    chord((make_test_task(h) for h in hosts))(post_uptest_all_procs.subtask((run.id,)))


@task
def post_uptest_all_procs(results, test_run_id):
    # record test run end time
    run = TestRun.objects.get(id=test_run_id)
    run.end = timezone.now()
    run.save()

    if run.has_failures():
        # Get just the failed TestResult objects.
        fail_results = run.tests.filter(passed=False)

        # Show output for each failed test in each failed result
        msg = '\n\n'.join(f.get_formatted_fails() for f in fail_results)


        send_event('scheduled uptest failures', msg,
                   tags=['scheduled', 'failed'])


@task
def _clean_host_releases(hostname):
    env.host_string = hostname
    env.abort_on_prompts = True
    env.user = settings.DEPLOY_USER
    env.password = settings.DEPLOY_PASSWORD
    env.linewise = True

    with always_disconnect():
        remote.clean_releases(execute=True)


@task
def scooper():
    # Clean up all active hosts
    for host in Host.objects.filter(active=True):
        _clean_host_releases.apply_async((host.name,), expires=120)


@task
def clean_old_builds():
    # select all builds older than BUILD_EXPIRATION_DAYS where file is not
    # None
    if settings.BUILD_EXPIRATION_DAYS is not None:
        cutoff = (timezone.now() -
                  datetime.timedelta(days=settings.BUILD_EXPIRATION_DAYS))

        old_builds = Build.objects.filter(end_time__lt=cutoff,
                                          file__isnull=False).order_by('-end_time')
        old_builds = set(old_builds)

        # Now filter out any builds that are currently in use
        all_procs = set()
        for host in Host.objects.filter(active=True):
            all_procs.update(host.get_procs())
        builds_in_use = {p.build for p in all_procs if p.build is not
                         None}
        old_builds.difference_update(builds_in_use)

        # Filter out any builds that are still within BUILD_EXPIRATION_COUNT
        def is_recent(build):
            newer_builds = Build.objects.filter(id__gte=build.id,
                                                app=build.app)
            rcnt = newer_builds.count() < settings.BUILD_EXPIRATION_COUNT
            return rcnt
        old_builds.difference_update([b for b in old_builds if is_recent(b)])


        # OK, we now have a set of builds that are older than both our cutoffs,
        # and definitely not in use.  Delete their files to free up space.
        for build in old_builds:
            # TODO: ensure that the mongo storage honors the delete method
            build.file.delete()
            build.status = 'expired'
            build.save()


@contextlib.contextmanager
def always_disconnect():
    """
    to address #18366, disconnect every time.
    """
    try:
        yield
    finally:
        fabric.network.disconnect_all()



class tmpredis(object):
    def __enter__(self):
        self.conn = redis.StrictRedis(
            **utils.parse_redis_url(settings.EVENTS_PUBSUB_URL))
        return self.conn

    def __exit__(self, type, value, tb):
        self.conn.connection_pool.disconnect()


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
