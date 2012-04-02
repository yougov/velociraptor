import logging
import tempfile
import os
import shutil
import posixpath

from celery.task import task as celery_task
from fabric.api import env
from django.conf import settings
import yaml

from deployment.models import Release, App, Build
from yg.deploy.fabric.system import deploy_parcel
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
    logging.info('deploying %s:%s to %s:%s' % (release, proc, host, port))

    try:
        # Pull the config yaml from the release and write it to a file.
        oshandle, tmp_path = tempfile.mkstemp()
        f = open(tmp_path, 'wb')
        f.write(yaml.safe_dump(release.config, default_flow_style=False))
        f.close()
        result = deploy_parcel(release.build.file.path, tmp_path, proc, port)
    finally:
        os.remove(tmp_path)
    return result


@celery_task()
def build_hg(app_id, tag):
    # call the assemble_hg function.
    app = App.objects.get(id=app_id)
    url = '%s#%s' % (app.repo_url, tag)
    with tmpdir():
        build_path = paver_build.assemble_hg_raw(url)
        # Create build record in DB and put tarball in MEDIA_ROOT/builds/
        filepath = settings.MEDIA_ROOT + 'builds/'
        if not os.path.exists(filepath):
            os.mkdir(filepath)
        shutil.move(build_path, filepath)
        build = Build(file='builds/' + posixpath.basename(build_path), app=app)
        build.save()
