import os
import posixpath
import sys
import hashlib

from paver.easy import task, sh

from pymongo import Connection
from gridfs import GridFS, NoFile

MONGO_HOST = 'vdeploydb.paix.yougov.local'
MONGO_PORT = 27017
MONGO_DB = 'yfiles'
MONGO_COLLECTION = 'fs'

# Relative path from pavement.py to your static files folder.
STATICFILES_ROOT = 'project/static'

# Prefix for all uploaded file paths.
# XXX THIS MUST BE CHANGED FOR OTHER BUILDS
BASEPATH = 'raptor'


def upload_file(fs, localname, remotename):

    with open(localname, 'rb') as f:
        contents = f.read()

        try:
            md5 = fs.get_last_version(remotename).md5
        except NoFile:
            md5 = ''

        if md5 == hashlib.md5(contents).hexdigest():
            print "%(remotename)s unchanged.  Skipping." % vars()
        else:
            print "Copying %(localname)s to gridfs:%(remotename)s" % vars()
            fs.put(contents, filename=remotename)


class chdir(object):
    def __init__(self, folder):
        self.orig_path = os.getcwd()
        self.temp_path = folder
    def __enter__(self):
        os.chdir(self.temp_path)
    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)


@task
def build():
    # We need both the current directory and the parent directory on sys.path
    # in order for collectstatic to work.
    here = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, here)

    sys.path.insert(0, os.path.join(here, 'project'))

    os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'
    sh('env/bin/python project/manage.py collectstatic --noinput')

    # look for static/ folder.  If found, copy each file therein into mongo
    # gridfs.
    if os.path.exists(STATICFILES_ROOT):
        print "SYNCING STATIC FILES TO GRIDFS"

        connection = Connection(MONGO_HOST, MONGO_PORT)
        db = connection[MONGO_DB]
        fs = GridFS(db, collection=MONGO_COLLECTION)

        with chdir(STATICFILES_ROOT):
            for root, dirs, files in os.walk('.'):
                # strip the "./" from the beginning of the root.
                cleanroot = root[2:]
                for filename in files:
                    localname = os.path.join(root, filename)
                    remotename = posixpath.join(BASEPATH, cleanroot, filename)
                    upload_file(fs, localname, remotename)
    else:
        print "no static/ folder found"
