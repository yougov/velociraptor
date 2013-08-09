import os
import subprocess
import shlex
import random
import string


here = os.path.dirname(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vr.server.settings'
os.environ['APP_SETTINGS_YAML'] = os.path.join(here, 'testconfig.yaml')


from django.contrib.auth.models import User


def sh(cmd):
    subprocess.call(shlex.split(cmd))


def dbsetup():
    here = os.path.dirname(os.path.abspath(__file__))
    project = os.path.dirname(here)
    os.chdir(here)
    sql = os.path.join(here, 'dbsetup.sql')
    sh('psql -f %s -U postgres' % sql)

    # Now create tables
    manage = os.path.join(project, 'manage.py')
    sh('python %s syncdb --noinput' % manage)
    sh('python %s migrate' % manage)


def randchars(num=8):
    return ''.join(random.choice(string.ascii_lowercase) for x in xrange(num))


def randurl():
    return 'http://%s/%s' % (randchars(), randchars())


def get_user():
    u = User(username=randchars())
    u.set_password('password123')
    u.is_admin = True
    u.is_staff = True
    u.save()
    return u
