from tambo import Transport


class Release(object):

    help = "The release sub-command"

    def __init__(self, argv):
        self.argv = argv
        self.parser = Transport(self.argv)

    def parse_args(self):
        print "Argument parsing done in the Release class"
