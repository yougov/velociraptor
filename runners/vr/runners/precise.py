"""
Start a proc inside a container with essential system folders bind-mounted in.
Supports Ubuntu 12.04 (Precise).
"""
import os
import pwd

from vr.common.paths import get_container_path, get_proc_path
from vr.runners.base import BaseRunner, mkdir, get_template


def main():
    runner = PreciseRunner()
    runner.main()


class PreciseRunner(BaseRunner):

    def make_proc_dirs(self):
        print "Making directories"
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

        volumes = getattr(self.config, 'volumes', [])
        for outside, inside in volumes:
            mkdir(os.path.join(container_path, inside.lstrip('/')))


    def write_proc_lxc(self):
        print "Writing proc.lxc"

        proc_path = get_proc_path(self.config)
        container_path = get_container_path(self.config)

        tmpl = get_template('precise.lxc')

        content = tmpl % {
            'proc_path': container_path,
        }

        content += self.get_lxc_volume_str()

        filepath = os.path.join(proc_path, 'proc.lxc')
        with open(filepath, 'wb') as f:
            f.write(content)


if __name__ == '__main__':
    main()
