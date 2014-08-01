from __future__ import print_function

import os

from vr.common.paths import (get_container_name, get_proc_path,
                             get_container_path, VR_ROOT)
from vr.runners.base import BaseRunner, mkdir, ensure_file, untar, get_template

IMAGES_ROOT = VR_ROOT + '/images'


def main():
    runner = ImageRunner()
    runner.main()


def ensure_image(name, url, images_root, md5, untar_to=None):
    """Ensure OS image at url has been downloaded and (optionally) unpacked."""
    image_dir_path = os.path.join(images_root, name)
    mkdir(image_dir_path)
    image_file_path = os.path.join(image_dir_path, os.path.basename(url))
    ensure_file(url, image_file_path, md5)
    if untar_to:
        prepare_image(image_file_path, untar_to)


def prepare_image(tarpath, outfolder, **kwargs):
    """Unpack the OS image stored at tarpath to outfolder.

    Prepare the unpacked image for use as a VR base image.

    """
    untar(tarpath, outfolder, **kwargs)

    # Some OSes have started making /etc/resolv.conf into a symlink to
    # /run/resolv.conf.  That prevents us from bind-mounting to that
    # location.  So delete that symlink, if it exists.
    resolv_path = os.path.join(outfolder, 'etc', 'resolv.conf')
    if os.path.islink(resolv_path):
        os.remove(resolv_path)
        with open(resolv_path, 'wb') as f:
            f.write('')


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
        print("Setting up", get_container_name(self.config))
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
        image_folder = self.get_image_folder()
        if os.path.exists(image_folder):
            print('OS image directory {} exists...not overwriting' \
                .format(image_folder))
            return

        ensure_image(
            self.config.image_name,
            self.config.image_url,
            IMAGES_ROOT,
            getattr(self.config, 'image_md5', None),
            self.get_image_folder()
        )

    def get_image_folder(self):
        return os.path.join(IMAGES_ROOT, self.config.image_name, 'contents')

    def get_proc_lxc_tmpl_ctx(self):
        return {
            'proc_path': get_container_path(self.config),
            'image_path': self.get_image_folder(),
        }
