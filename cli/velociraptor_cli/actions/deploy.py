from tambo import Transport


class Deploy(object):

    help = "The deploy sub-command"

    def __init__(self, argv):
        self.argv = argv
        self.parser = Transport(self.argv)

    def parse_args(self):
        print "Argument parsing done in the deploy class"
