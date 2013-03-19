import os

# Make sure Django settings are loaded.
os.environ['DJANGO_SETTINGS_MODULE'] = 'vr.settings'
from django.core import management

def start_celery():
    management.call_command('celeryd')

def start_celerybeat():
    management.call_command('celerybeat', pidfile=None)
