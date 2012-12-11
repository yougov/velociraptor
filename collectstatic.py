#!/usr/bin/env python
"""
This script is used to run "manage.py collectstatic" and then push the
collected files up to GridFS. It should be called by the post_compile hook in
the Heroku python buildpack.  Post compile hooks may change.

See https://github.com/heroku/heroku-buildpack-python/pull/42
"""

import os
import posixpath
import sys
import hashlib
import subprocess
import shlex

from pymongo import Connection
from gridfs import GridFS, NoFile

from raptor.util import chdir

MONGO_HOST = 'vdeploydb.paix.yougov.local'
MONGO_PORT = 27017
MONGO_DB = 'yfiles'
MONGO_COLLECTION = 'fs'

# Relative path from pavement.py to your static files folder.
STATICFILES_ROOT = 'project/static'

# Prefix for all uploaded file paths.
# XXX THIS MUST BE CHANGED FOR OTHER BUILDS
BASEPATH = 'raptor'


def sh(cmd):
    subprocess.check_call(shlex.split(cmd))


def indent(msg):
    print "       %s" % msg


def heading(msg):
    print "-----> %s" % msg


def upload_file(fs, localname, remotename):

    with open(localname, 'rb') as f:
        contents = f.read()

        try:
            md5 = fs.get_last_version(remotename).md5
        except NoFile:
            md5 = ''

        if md5 == hashlib.md5(contents).hexdigest():
            indent("%(remotename)s unchanged.  Skipping." % vars())
        else:
            indent("Copying %(localname)s to gridfs:%(remotename)s" % vars())
            fs.put(contents, filename=remotename)


def main():
    # We need both the current directory and the parent directory on sys.path
    # in order for collectstatic to work.
    here = os.path.dirname(os.path.realpath(__file__))
    sys.path.insert(0, here)

    sys.path.insert(0, os.path.join(here, 'project'))

    os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'
    sh('python project/manage.py collectstatic --noinput')

    # look for static/ folder.  If found, copy each file therein into mongo
    # gridfs.
    if os.path.exists(STATICFILES_ROOT):
        heading("Syncing static files to GridFS")

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

if __name__ == '__main__':
    main()
