from __future__ import print_function

import os
import stat

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

    char_devices = (
        ('/dev/null', (1, 3), 0666),
        ('/dev/zero', (1, 5), 0666),
        ('/dev/random', (1, 8), 0444),
        ('/dev/urandom', (1, 9), 0444),
    )

    def setup(self):
        print("Setting up", get_container_name(self.config))
        mkdir(IMAGES_ROOT)
        self.ensure_image()
        self.make_proc_dirs()
        self.ensure_build()
        self.ensure_char_devices()
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

    def ensure_char_devices(self):
        for path, devnums, perms in self.char_devices:
            fullpath = get_container_path(self.config) + path
            ensure_char_device(fullpath, devnums, perms)


def ensure_char_device(path, devnums, perms):
    # Python uses the OS mknod(2) implementation which modifies the mode based
    # on the umask of the running process (at least on some Linuxes that were
    # tested).  Set this to 0 to make mknod apply the perms you actually
    # specify
    if not os.path.exists(path):
        with tmp_umask(0):
            print("mknod -m %s %s c %s %s" % (perms path, devnums[0], devnums[1]))
            mkdir(os.path.dirname(path))
            mode = (stat.S_IFCHR | perms)
            os.mknod(path, mode, os.makedev(*devnums))
    else:
        print("%s already exists.  Skipping" % path)


class tmp_umask(object):
    """Context manager for temporarily setting the process umask"""
    def __init__(self, tmp_mask):
        self.tmp_mask = tmp_mask

    def __enter__(self):
        self.orig_mask = os.umask(self.tmp_mask)

    def __exit__(self, type, value, traceback):
        os.umask(self.orig_mask)

