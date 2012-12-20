import xmlrpclib

# A fake Supervisor xmlrpc interface.
class FakeSupervisor(object):
    # Set this at test time in order to fake an exception.
    exception = None

    # Set this dict in order to control what data comes back from the
    # getAllProcessInfo and getProcessInfo calls.  (Slightly tweaked to include
    # a 'host' key.)
    # XXX A lot of tests rely on this bit of data.
    process_info = {
        'dummyproc': {
            'description': 'pid 5556, uptime 16:05:53',
            'exitstatus': 0,
            'group':  'dummyproc',
            'logfile':  '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
            'name':  'dummyproc',
            'now': 1355897986,
            'pid': 5556,
            'spawnerr':  '',
            'start': 1355897986,
            'state': 20,
            'statename':  'RUNNING',
            'stderr_logfile':  '/tmp/pub.log',
            'stdout_logfile':  '/var/log/supervisor/dummyproc-stdout---supervisor-cYv5Q2.log',
            'stop': 1355897986,
            'host': 'somewhere'},
        'node_example-v2-local-f96054b7-web-5003': {
            'description': 'Exited too quickly (process log may have details)',
            'exitstatus': 0,
            'group': 'node_example-v2-local-f96054b7-web-5003',
            'logfile': '/apps/procs/node_example-v2-local-f96054b7-web-5003/log',
            'name': 'node_example-v2-local-f96054b7-web-5003',
            'now': 1355955939,
            'pid': 0,
            'spawnerr': 'Exited too quickly (process log may have details)',
            'start': 1355898065,
            'state': 200,
            'statename': 'FATAL',
            'stderr_logfile': '/var/log/supervisor/node_example-v2-local-f96054b7-web-5003-stderr---supervisor-gL_lvl.log',
            'stdout_logfile': '/apps/procs/node_example-v2-local-f96054b7-web-5003/log',
            'stop': 1355898065}}

    def _fake_fault(self):
        if self.exception:
            raise self.exception

    def getProcessInfo(self, name):
        self._fake_fault()
        try:
            return self.process_info[name]
        except KeyError:
            # Raise exception like supervisor would when asked to return data
            # on nonexistent Proc.
            raise xmlrpclib.Fault(10, 'BAD_NAME: %s' % name)

    def getAllProcessInfo(self):
        self._fake_fault()
        return self.process_info.values()

class FakeRPC(object):
    def __init__(self):
        self.supervisor = FakeSupervisor()

