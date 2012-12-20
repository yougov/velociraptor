import os
import shutil
import tempfile
import urlparse


class tmpdir(object):
    """Context manager for putting you into a temporary directory on enter
    and deleting the directory on exit
    """
    def __init__(self):
        self.orig_path = os.getcwd()

    def __enter__(self):
        self.temp_path = tempfile.mkdtemp()
        os.chdir(self.temp_path)
        return self.temp_path

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)
        shutil.rmtree(self.temp_path, ignore_errors=True)


class chdir(object):
    def __init__(self, folder):
        self.orig_path = os.getcwd()
        self.temp_path = folder

    def __enter__(self):
        os.chdir(self.temp_path)

    def __exit__(self, type, value, traceback):
        os.chdir(self.orig_path)


class CommandException(Exception):
    """
    Custom exception class for displaying nice input from failed envoy
    commands.  Accepts an envoy command result object on init.
    """

    def __init__(self, result):
        message = ("Command '%(command)s' failed with status code "
                   "%(status_code)s.\n"
                   "std_out: %(std_out)s\n"
                   "std_err: %(std_err)s\n") % {
                       'command': ' '.join(result.command),
                       'status_code': result.status_code,
                       'std_out': result.std_out,
                       'std_err': result.std_err,
                   }
        super(CommandException, self).__init__(message)


def parse_redis_url(url):
    """
    Given a url like redis://localhost:6379/0, return a dict with host, port,
    and db members.
    """
    parsed = urlparse.urlsplit(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port,
        'db': int(parsed.path.replace('/', '')),
    }
