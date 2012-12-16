import xmlrpclib
from datetime import datetime

import isodate


class Host(object):
    def __init__(self, name, rpc_port=9001):
        self.name = name
        self.rpc_port = rpc_port

    @property
    def rpc(self):
        return xmlrpclib.Server('http://%s:%s' % (self.name,
                                                  self.rpc_port)).supervisor

    def get_proc(self, name):
        return Proc(self, self.rpc.getProcessInfo(name))

    def get_procs(self):
        all_data = self.rpc.getAllProcessInfo()
        return [Proc(self, d) for d in all_data]

    def __repr__(self):
        info = {
            'cls': self.__class__.__name__,
            'name': self.name,
            'port': self.rpc_port,
        }
        return "%(cls)s('%(name)s', %(port)s)" % info


class Proc(object):
    """
    A representation of a proc running on a host.  Must be initted with the
    hostname and a dict of data structured like the one you get back from
    Supervisor's XML RPC interface.
    """

    def __init__(self, host, data):
        self.host = host
        self._data = data

        # These fields are returned from the RPC as unix times, or 0 when not
        # applicable.  Make those datetime.datetime and None.  When initted
        # from cached Proc data, they'll be isoformat timestamps.
        unixtime_fields = ('now', 'start', 'stop')

        for k in self._data:
            v = self._data[k]
            if k in unixtime_fields:
                if v == 0 or v is None:
                    setattr(self, k, None)
                elif isinstance(v, int):
                    setattr(self, k, datetime.fromtimestamp(self._data[k]))
                else:  # Not an int or None, assume it's a isodate string
                    setattr(self, k, isodate.parse_datetime(v))
            else:
                setattr(self, k, v)

        # The names returned from Supervisor have a bunch of metadata encoded
        # in them (at least until we can get a Supervisor RPC plugin to return
        # it).  Parse that out and set attributes.
        for k, v in self._parse_name().items():
            setattr(self, k, v)

        # We also set some convenience attributes for JS/CSS.  Consider pushing
        # the creation of these out to the JS layer.
        self.jsname = self.name.replace('.', 'dot')
        self.id = '%s-%s' % (self.hostname, self.name)

    def _parse_name(self):
        try:
            app_name, version, recipe_name, rel_hash, proc_name, port = self.name.split('-')

            return {
                'app_name': app_name,
                'version': version,
                'recipe_name': recipe_name,
                'hash': rel_hash,
                'proc_name': proc_name,
                'port': int(port)
            }
        except ValueError:
            return {
                'app_name': '~UNKNOWN',
                'version': 'UNKNOWN',
                'recipe_name': 'UNKNOWN',
                'hash': 'UNKNOWN',
                'proc_name': self.name,
                'port': 0
            }

    def __repr__(self):
        return "<Proc %s>" % self.name

    @property
    def hostname(self):
        return self.host.name

    def shortname(self):
        return '%s-%s' % (self.app, self.procname)

    def as_node(self):
        """
        Return host:port, as needed by the balancer interface.
        """
        return '%s:%s' % (self.hostname, self.port)

    def as_dict(self):
        data = {}
        for k, v in self.__dict__.items():
            if isinstance(v, (basestring, int)):
                data[k] = v
            elif isinstance(v, datetime):
                data[k] = v.isoformat()
            elif v is None:
                data[k] = v
        data['host'] = self.hostname
        return data
