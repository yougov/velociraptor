#!/usr/bin/env python

import argparse

import yaml

from vr.imager.build import cmd_build, cmd_shell
from vr.common.models import ConfigData


commands = {
    'build': cmd_build,
    'shell': cmd_shell,
}


def get_command(name):
    try:
        return commands[name]
    except KeyError:
        raise SystemExit("'%s' is not a valid command" % name)


class ImageData(ConfigData):
    _required = [
        'base_image_url',
        'base_image_name',
        'new_image_name',
        'script_url',
    ]

    _optional = [
        'base_image_md5',
        'new_image_md5',
        'env',
    ]

    def __repr__(self):
        print('<ImageData: %s+%s>' % (self.base_image_name, self.script_url))


def main():

    cmd_list = ', '.join(sorted(commands.keys()))

    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='One of %s' % cmd_list,
                        type=get_command)
    parser.add_argument('file', help="Path to image.yaml file.")
    args = parser.parse_args()

    with open(args.file, 'rb') as f:
        image_data = ImageData(yaml.safe_load(f))
    args.command(image_data)
