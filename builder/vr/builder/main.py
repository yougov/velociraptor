#!/usr/bin/env python

import argparse

import yaml

from vr.builder.build import cmd_build
from vr.common.models import ConfigData



def cmd_shell(build_data):
    cmd_build(build_data, runner_cmd='shell', make_tarball=False)

commands = {
    'build': cmd_build,
    'shell': cmd_shell,
}

def get_command(name):
    try:
        return commands[name]
    except KeyError:
        raise SystemExit("'%s' is not a valid command" % name)


class BuildData(ConfigData):
    _required = [
        'app_name',
        'app_repo_url',
        'app_repo_type',
        'version',
    ]

    _optional = [
        'buildpack_url',
        'buildpack_urls',
        'buildpack_version',
        'image_url',
        'image_name',
        'image_md5',
        'build_md5',
        'release_data',
    ]

    def __init__(self, dct):
        super(BuildData, self).__init__(dct)

        # must provide buildpack_urls or buildpack_url
        if self.buildpack_urls is None and self.buildpack_url is None:
            raise ValueError('Must provide either buildpack_url or '
                             'buildpack_urls')

    def __repr__(self):
        print '<BuildData: %s-%s>' % (self.app_name, self.version)


def main():

    cmd_list = ', '.join(sorted(commands.keys()))

    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='One of %s' % cmd_list,
                        type=get_command)
    parser.add_argument('file', help="Path to build.yaml file.")
    args = parser.parse_args()

    with open(args.file, 'rb') as f:
        build = BuildData(yaml.safe_load(f))
    args.command(build)
