import logging
import tempfile
import os
import shutil
import posixpath

from celery.task import task as celery_task
from fabric.api import env
from mongoengine.django.storage import GridFSStorage
import yaml

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
def deploy(release_id, host, proc, port, user, password):
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
        f.write(yaml.safe_dump(release.config, default_flow_style=False))
        f.close()
        # pull the build out of gridfs, write it to a temporary location, and
        # deploy it. 
        build_name = posixpath.basename(release.build.file.name)
        fs = GridFSStorage()
        local_build = open(build_name, 'wb')
        gridfs_build = fs.open(release.build.file.name)
        local_build.write(gridfs_build.read())

        local_build.close()
        gridfs_build.close()

        result = deploy_parcel(build_name, 'settings.yaml', proc, port)
    return result


@celery_task()
def build_hg(app_id, tag):
    # call the assemble_hg function.
    app = App.objects.get(id=app_id)
    url = '%s#%s' % (app.repo_url, tag)
    with tmpdir():
        build_path = paver_build.assemble_hg_raw(url)

        # Save the file to Mongo GridFS
        fs = GridFSStorage()
        localfile = open(build_path, 'r')
        filepath = 'builds/' + posixpath.basename(build_path)
        fs.save(filepath, localfile)
        localfile.close()

        # Create a record of the build in the db
        build = Build(file=filepath, app=app)
        build.save()


@celery_task()
def delete_proc(host, proc, user, password):
    env.host_string = host
    env.abort_on_prompts = True
    env.user=user
    env.password=password
    logging.info('%s deleting %s on %s' % (user, proc, host))
    fab_delete_proc(proc)
