from __future__ import with_statement

import os
import subprocess
import itertools
import tempfile
import time
import sys

import py.test

from yg.lockfile import FileLock, FileLockTimeout

def test_FileLock_basic():
    tfile, filename = tempfile.mkstemp()
    os.close(tfile)
    os.remove(filename)
    l = FileLock(filename)
    l2 = FileLock(filename, timeout=0.2)
    assert not l.is_locked()
    l.acquire()
    assert l.is_locked()
    l.release()
    assert not l.is_locked()
    with l:
        assert os.path.isfile(filename)
        py.test.raises(FileLockTimeout, l2.acquire)
    assert not l.is_locked()
    l2.acquire()
    assert l2.is_locked()
    l2.release()

def lines(stream):
    """
    I can't figure out how to get the subprocess module to feed me
    line-buffered output from a sub-process, so I grab the output byte
    by byte and assemble it into lines.
    """
    buf = ''
    while True:
        dat = stream.read(1)
        if dat:
            buf += dat
            if dat == '\n':
                yield buf
                buf = ''
        if not dat and buf:
            yield buf
        if not dat:
            break

def test_FileLock_process_killed():
    """
    If a subprocess fails to release the lock, it should be released
    and available for another process to take it.
    """
    tfile, filename = tempfile.mkstemp()
    os.close(tfile)
    os.remove(filename)
    cmd = [sys.executable, '-u', '-c', 'from yg.lockfile '
        'import FileLock; import time; l = FileLock(%(filename)r); '
        'l.acquire(); print "acquired", l.lockfile; '
        '[time.sleep(1) for x in xrange(10)]' % vars()]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out = itertools.takewhile(lambda l: 'acquired' not in l,
        lines(proc.stdout))
    tuple(out) # wait for 'acquired' to be printed by subprocess

    l = FileLock(filename, timeout=0.2)
    py.test.raises(FileLockTimeout, l.acquire)
    proc.kill()
    time.sleep(.5)
    l.acquire()
    l.release()
