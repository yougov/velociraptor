# Define Celery celery_tasks here.

import time
import logging

from celery.task import task as celery_task
from fabric.api import env

from deployment.fabfile import get_date
from deployment.models import Release
from yg.deploy.fabric.system import deploy_parcel

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
    return deploy_parcel(release.build.file.path, release.config.path,
                         proc, port)


# DUMMY TASKS BELOW HERE.

@celery_task()
def get_host_date(hostname):
    env.host_string = hostname
    env.abort_on_prompts = True
    env.celery_task = get_host_date
    get_host_date.update_state(state='PROGRESS', meta='Started')
    time.sleep(20)
    return get_date()

