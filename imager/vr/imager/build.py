import os
import pkg_resources
import shutil
import stat
import subprocess
import tarfile
import textwrap

from vr.common.utils import tmpdir, get_lxc_version, get_lxc_network_config
from vr.runners.image import ensure_image, IMAGES_ROOT
from vr.runners.base import ensure_file


def cmd_build(image_data):
    run_image(image_data, make_tarball=True)


def cmd_shell(image_data):
    run_image(image_data, cmd='/bin/bash', make_tarball=False)


def run_image(image_data, cmd=None, user='root', make_tarball=False):
    outfolder = os.getcwd()
    with tmpdir() as here:
        # download image
        image_path = os.path.realpath('img')
        print "Ensuring presence of image from " + image_data.base_image_url
        ensure_image(image_data.base_image_name,
                     image_data.base_image_url,
                     IMAGES_ROOT,
                     image_data.base_image_md5,
                     untar_to=image_path)

        # write LXC config file
        tmpl = get_template('base_image.lxc')
        content = tmpl % {
            'image_path': image_path,
            'network_config': get_lxc_network_config(get_lxc_version()),
        }
        lxc_file_path = os.path.join(here, 'imager.lxc')
        print("Writing %s" % lxc_file_path)
        with open(lxc_file_path, 'wb') as f:
            f.write(content)

        lxc_name = 'build_image-' + image_data.new_image_name

        script_path = None
        if cmd is None:
            # copy bootstrap script into place and ensure it's executable.
            script = os.path.basename(image_data.script_url)
            script_path = os.path.join(image_path, script)
            if os.path.exists(image_data.script_url):
                shutil.copy(image_data.script_url, script_path)
            else:
                ensure_file(image_data.script_url, script_path)
            st = os.stat(script_path)
            os.chmod(
                script_path,
                st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )
            real_cmd = '/' + script
        else:
            real_cmd = cmd

        # Call lxc-start, passing in our LXC config file and telling it to run
        # our build script inside the container.
        lxc_args = [
            'lxc-start',
            '--name', lxc_name,
            '--rcfile', lxc_file_path,
            '--',
            real_cmd,
        ]
        env = {
            'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:'
                    '/sbin:/bin:/usr/games',
            'HOME': '/root',
        }
        env.update(image_data.env or {})
        if 'TERM' in os.environ:
            env['TERM'] = os.environ['TERM']
        subprocess.check_call(lxc_args, env=env, stderr=subprocess.STDOUT)

        # remove build script if we used one.
        if cmd is not None:
            os.remove(script_path)

        if make_tarball:
            tardest = os.path.join(outfolder, '%s.tar.gz' %
                                   image_data.new_image_name)
            print "Compressing image to " + tardest
            with tarfile.open(tardest, 'w:gz') as tar:
                tar.add(image_path, arcname='')


def get_template(name):
    """
    Look for 'name' in the vr.runners.templates folder.  Return its contents.
    """
    path = pkg_resources.resource_filename('vr.imager', 'templates/' + name)
    with open(path, 'r') as f:
        return f.read()
