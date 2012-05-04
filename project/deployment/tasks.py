import logging
import tempfile
import os
import shutil
import posixpath
import re
import datetime

import fabric.network
from celery.task import task as celery_task
from fabric.api import env
from django.core.files.storage import default_storage

from deployment.models import Release, App, Build
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
def deploy(release_id, profile, host, proc, port, user, password):
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

        result = deploy_parcel(build_name, 'settings.yaml', profile, proc, port)

    # to address #18366, disconnect every time. This may have performance
    #  implications when we deploy multiple releases to the same host.
    fabric.network.disconnect_all()

    return result


@celery_task()
def build_hg(app_id, tag):
    # call the assemble_hg function.
    app = App.objects.get(id=app_id)
    url = '%s#%s' % (app.repo_url, tag)
    with tmpdir():
        build_path = paver_build.assemble_hg_raw(url)

        # Save the file to Mongo GridFS
        localfile = open(build_path, 'r')
        name = posixpath.basename(build_path)
        filepath = 'builds/' + name
        default_storage.save(filepath, localfile)
        localfile.close()

        # Create a record of the build in the db
        # Parse the timestamp from the name, which should look like this:
        # 'panelcare2-1.0.3-2012-04-19T00-56.tar.bz2'
        name = name.replace('.tar.bz2', '')
        dts = datetime.datetime(*[int(x) for x in re.split('[-T]', name)[2:]])
        build = Build(file=filepath, app=app, tag=tag, time=dts)
        build.save()


@celery_task()
def delete_proc(host, proc, user, password):
    env.host_string = host
    env.abort_on_prompts = True
    env.user=user
    env.password=password
    logging.info('%s deleting %s on %s' % (user, proc, host))
    fab_delete_proc(proc)
