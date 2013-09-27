from __future__ import print_function

import sys
import os
import subprocess
import shutil
import tempfile
import urlparse
from datetime import datetime

import isodate
import six


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
    Custom exception class for displaying nice input from failed commands.
    Accepts an CommandResult object on init.
    """

    def __init__(self, result):
        message = ("Command '%(command)s' failed with status code "
                   "%(status_code)s.\n"
                   "output: %(output)s\n") % {
                       'command': result.command,
                       'status_code': result.status_code,
                       'output': result.output,
                   }
        super(CommandException, self).__init__(message)


class CommandResult(object):
    def __init__(self, command, output, status_code):
        self.command = command
        self.output = six.text_type(output, 'ascii', 'replace')
        self.status_code = status_code

    def __repr__(self):
        return '<CommandResult: %s,%s>' % (self.status_code, self.command)

    def raise_for_status(self):
        if self.status_code != 0:
            raise CommandException(self)


def run(command, verbose=False):
    """
    Run a shell command.  Capture the stdout and stderr as a single stream.
    Capture the status code.

    If verbose=True (the default), then print command and the output to the
    terminal.

    """
    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    output = ""
    status_code = None
    if verbose:
        print("run:", command)
    while status_code is None:
        status_code = p.poll()
        line = p.stdout.readline()
        if verbose:
            sys.stdout.write(line)
        output += line
    return CommandResult(command, output, status_code)


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


utc = isodate.FixedOffset(0, 0, 'UTC')

def utcfromtimestamp(ts):
    """
    Given a UNIX timestamp, return a Python datetime with the tzinfo explicitly
    set to UTC (as opposed to datetime.utcfromtimestamp, which returns a naive
    datetime with UTC values).
    """
    dt = datetime.utcfromtimestamp(ts)
    return dt.replace(tzinfo=utc)
