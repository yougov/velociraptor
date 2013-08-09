import os
import tempfile
import shutil
import xmlrpclib

from vr.common import repo
from vr.common.utils import run

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


class tmprepo(object):
    """
    Context manager for creating a tmp dir, unpacking a specified repo tarball
    inside it, cd-ing in there, letting you run stuff, and then cleaning up and
    cd-ing back where you were when it's done.
    """
    def __init__(self, tarball, vcs_type, repo_class=None):
        # Repo tarballs must be in the same directory as this file.
        here = os.path.dirname(os.path.abspath(__file__))
        self.tarball = os.path.join(here, tarball)
        self.vcs_type = vcs_type
        self.orig_path = os.getcwd()
        self.repo_class = repo_class or repo.Repo

    def __enter__(self):
        self.temp_path = tempfile.mkdtemp()
        os.chdir(self.temp_path)
        cmd = 'tar -zxf %s --strip-components 1' % self.tarball
        result = run(cmd)
        result.raise_for_status()
        return self.repo_class('./', vcs_type=self.vcs_type)

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)
        shutil.rmtree(self.temp_path, ignore_errors=True)
