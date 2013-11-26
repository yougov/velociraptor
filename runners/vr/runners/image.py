import os

import requests
from vr.common.paths import (get_container_name, get_proc_path,
                             get_container_path, VR_ROOT)
from vr.runners.base import (BaseRunner, mkdir, file_md5, ensure_file, untar,
                             get_template)


IMAGES_ROOT = VR_ROOT + '/images'

def main():
    runner = ImageRunner()
    runner.main()

class ImageRunner(BaseRunner):
    """
    A runner that launches apps inside a container built around a whole OS
    image tarball.  Requires that the proc config contain keys for 'image_url'
    and 'image_name'.

    Image tarballs are stored in /apps/images/<image_name>/<filename>.

    Unpacked images are stored in /apps/images/<image_name>/contents
    """

    lxc_template_name = 'image.lxc'

    def setup(self):
        print "Setting up", get_container_name(self.config)
        mkdir(IMAGES_ROOT)
        self.ensure_image()
        self.make_proc_dirs()
        self.ensure_build()
        self.write_proc_lxc()
        self.write_settings_yaml()
        self.write_proc_sh()
        self.write_env_sh()


    def ensure_image(self):
        """
        Ensure that config.image_url has been downloaded and unpacked.
        """
        mkdir(os.path.join(IMAGES_ROOT, self.config.image_name))
        image_url = self.config.image_url
        base = os.path.basename(image_url)
        image_file_path = os.path.join(IMAGES_ROOT, self.config.image_name, base)
        expected_md5 = getattr(self.config, 'image_md5', None)
        ensure_file(image_url, image_file_path, expected_md5)
        untar(image_file_path, self.get_image_folder())

        # Some OSes have started making /etc/resolv.conf into a symlink to
        # /run/resolv.conf.  That prevents us from bind-mounting to that
        # location.  So delete that symlink, if it exists.
        resolv_path = os.path.join(self.get_image_folder(), 'etc',
                                   'resolv.conf')
        if os.path.islink(resolv_path):
            os.remove(resolv_path)
            with open(resolv_path, 'wb') as f:
                f.write('')

    def get_image_folder(self):
        return os.path.join(IMAGES_ROOT, self.config.image_name, 'contents')


    def write_proc_lxc(self):
        print "Writing proc.lxc"

        proc_path = get_proc_path(self.config)
        container_path = get_container_path(self.config)

        tmpl = get_template(self.lxc_template_name)

        content = tmpl % {
            'proc_path': container_path,
            'image_path': self.get_image_folder(),
        }

        content += self.get_lxc_volume_str()

        filepath = os.path.join(proc_path, 'proc.lxc')
        with open(filepath, 'wb') as f:
            f.write(content)
