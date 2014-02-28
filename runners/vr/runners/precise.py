"""
Start a proc inside a container with essential system folders bind-mounted in.
Supports Ubuntu 12.04 (Precise).
"""

from __future__ import print_function

import os
import pwd

from vr.common.paths import get_container_path, get_proc_path
from vr.runners.base import BaseRunner, mkdir, get_template


def main():
    runner = PreciseRunner()
    runner.main()


class PreciseRunner(BaseRunner):

    lxc_template_name = 'precise.lxc'

    def make_proc_dirs(self):
        print("Making directories")
        proc_path = get_proc_path(self.config)
        container_path = get_container_path(self.config)
        mkdir(proc_path)
        mkdir(container_path)

        # make tmp dir.  Set owner
        tmp_path = os.path.join(container_path, 'tmp')
        mkdir(tmp_path)
        user = pwd.getpwnam(self.config.user)
        os.chown(tmp_path, user.pw_uid, user.pw_gid)

        # make mount points too
        mountpoints = (
            'bin',
            'dev',
            'etc',
            'lib',
            'lib64',
            'opt',
            'usr',
            'proc',
            'run',
            'sys',
            'dev/pts',
        )
        for path in mountpoints:
            mkdir(os.path.join(container_path, path))

        volumes = getattr(self.config, 'volumes', []) or []
        for outside, inside in volumes:
            mkdir(os.path.join(container_path, inside.lstrip('/')))


if __name__ == '__main__':
    main()
