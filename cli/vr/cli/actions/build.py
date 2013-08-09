from tambo import Transport


class Build(object):

    help = "The build sub-command"

    def __init__(self, argv):
        self.argv = argv
        self.parser = Transport(self.argv)

    def parse_args(self):
        print "Argument parsing done in the Build class"
