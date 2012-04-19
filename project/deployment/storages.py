import urlparse

from django.core.files.storage import Storage
from django.conf import settings

from pymongo import Connection
from gridfs import GridFS

class GridFSStorage(Storage):
    def __init__(self, connection=None, host=None, port=None, db=None,
                 collection=None, base_url=None):
        # All settings have defaults, which can be overridden in settings.py,
        # which can themselves be overridden with explicit arguments passed to
        # the constructor.

        # If passed a pymongo connection object, then skip all the host/port
        # stuff.  This allows for re-using a Connection, which is important in
        # a gevent-type situation.
        if connection is None:
            # Default host is 'localhost'
            host = host or getattr(settings, 'GRIDFS_HOST', 'localhost')

            # Default port is 27017
            port = port or getattr(settings, 'GRIDFS_PORT', 27017)

            connection = Connection(host, port)

        # Default db is 'test'
        db = db or getattr(settings, 'GRIDFS_DB', 'test')

        # Default collection is 'fs'
        collection = collection or getattr(settings, 'GRIDFS_COLLECTION', 'fs')

        self.db = connection[db]
        self.fs = GridFS(self.db, collection=collection)

        self.base_url = base_url or settings.MEDIA_URL

    def _save(self, name, content):
        self.fs.put(content, filename=name)
        return name

    def _open(self, name, *args, **kwars):
        return self.fs.get_last_version(filename=name)

    def delete(self, name):
        oid = self.fs.get_last_version(filename=name)._id
        self.fs.delete(oid)

    def exists(self, name):
        return self.fs.exists({'filename': name})

    def size(self, name):
        return self.fs.get_last_version(filename=name).length

    def url(self, name):
        if self.base_url is None:
            raise NotImplementedError()
        return urlparse.urljoin(self.base_url, name).replace('\\', '/')
