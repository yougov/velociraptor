# Define Celery celery_tasks here.

import time

from celery.task import task as celery_task
from fabric.api import env

from deployment.fabfile import get_os_version, install_pycrypto



@celery_task()
def add(x, y):
    return x + y

@celery_task()
def wait_and_count(ceil, secs=1):
    for n in xrange(ceil):
        print n
        time.sleep(secs)

    return "blerg"

@celery_task()
def get_host_os_version(hostname, user, password):
    env.host_string = hostname
    env.user = user
    env.password = password
    env.abort_on_prompts = True
    return get_os_version()

@celery_task()
def install_pycrypto_celery_task(hostname):
    env.host_string = 'brent.tubbs@' + hostname
    return install_pycrypto()
