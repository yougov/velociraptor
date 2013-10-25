"""
Supervisor RPC plugin for Velociraptor.

To configure Supervisor to use this interface in addition to 
its built in RPC interface, put the following in your Supervisor config:

[rpcinterface:velociraptor]
supervisor.rpcinterface_factory = vr.agent.rpc:make_interface
"""

import os
import posixpath

import yaml
import psutil
from supervisor.rpcinterface import SupervisorNamespaceRPCInterface
from supervisor.options import make_namespec

def make_interface(supervisord, **config):
    apps_root = config.get('apps_root', '/apps')
    return VelociraptorRPC(supervisord, apps_root)

class VelociraptorRPC(object):
    def __init__(self, supervisord, apps_root):
        self.supervisord = supervisord
        self.apps_root = apps_root


        self.supd_rpc = SupervisorNamespaceRPCInterface(supervisord)

    def _get_proc_path(self, procname):
        path = posixpath.join(self.apps_root, 'procs', procname)
        if os.path.isdir(path):
            return path
        return None

    # TODO: Move path creating functions into a vr.common.paths module, so they
    # can be re-used between all parts of the system.
    def _get_proc_yaml_path(self, procname):
        # Given a procname, return the path to its proc.yaml file, if it
        # exists
        proc_path = self._get_proc_path(procname)
        if proc_path is None:
            return None
        proc_yaml_path = os.path.join(proc_path, 'proc.yaml')
        if os.path.isfile(proc_yaml_path):
            return proc_yaml_path

    def get_velociraptor_info(self, procname):
        path = self._get_proc_yaml_path(procname)
        if path:
            with open(path, 'rb') as f:
                return yaml.safe_load(f)
        return {}

    def get_psinfo(self, procname, pid=None):
        if pid is None:
            pid = self.supd_rpc.getProcessInfo(procname)['pid']
        p = psutil.Process(pid)
        iocounters = p.get_io_counters()
        meminfo = p.get_memory_info()
        cputimes = p.get_cpu_times()
        ctx_switches = p.get_num_ctx_switches()
        return {
            'cmdline': p.cmdline,
            'cwd': p.getcwd(),
            'read_count': iocounters.read_count,
            'write_count': iocounters.write_count,
            'read_bytes': iocounters.read_bytes,
            'write_bytes': iocounters.write_bytes,
            'num_fds': p.get_num_fds(),
            'num_threads': p.get_num_threads(),
            'num_ctx_switches_voluntary': ctx_switches.voluntary,
            'num_ctx_switches_involuntary': ctx_switches.involuntary,
            'cpu_percent': p.get_cpu_percent(0),
            'cpu_time_user': cputimes.user,
            'cpu_time_system': cputimes.system,
            'memory_percent': p.get_memory_percent(),
            'memory_rss': meminfo.rss,
            'memory_vms': meminfo.vms,
            'status': p.status,
        }

    def get_proc_info(self, procname, supd_info=None):
        supd_info = supd_info or self.supd_rpc.getProcessInfo(procname)
        return {
            'supervisor': supd_info,
            'velociraptor': self.get_velociraptor_info(procname),
            'psinfo': self.get_psinfo(procname, pid=supd_info['pid']),
        }

    def get_all_procs_info(self):
        supds = self.supd_rpc.getAllProcessInfo()
        return [self.get_proc_info(p['name'], p) for p in supds]