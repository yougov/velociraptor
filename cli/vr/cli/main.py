"""
vr: A command line tool to interact with the Velociraptor API.

Global Options:
--log, --logging    Set the level of logging. Acceptable values:
                    debug, warning, error, critical

"""


import sys

from tambo import Transport

import vr.cli
from vr.cli import actions


class Velociraptor(object):

    mapper = {
        'build': actions.Build,
        'release': actions.Release,
        'deploy': actions.Deploy
    }

    def __init__(self, argv=None, parse=True):
        if argv is None:
            argv = sys.argv
        if parse:
            self.main(argv)

    def main(self, argv):
        options = [['--log', '--logging']]
        parser = Transport(argv, mapper=self.mapper,
                           options=options, check_help=False,
                           check_version=False)
        parser.parse_args()
        vr.cli.config['verbosity'] = parser.get('--log', 'info')
        parser.catch_help = "%s%s" % (__doc__, parser.subhelp())
        parser.catch_version = '0.0.1'
        parser.mapper = self.mapper
        if len(argv) <= 1:
            return parser.print_help()
        parser.dispatch()
        parser.catches_help()
        parser.catches_version()
