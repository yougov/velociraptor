"""
Constants and functions for determining where Velociraptor puts things at
deploy time.  All of the get_* functions accept a ProcData object, which is is
built from a dict parsed out of a proc.yaml file.
"""
import os

BUILDS_ROOT = '/apps/builds'
PROCS_ROOT = '/apps/procs'
RELEASES_ROOT = '/apps/releases'


def get_container_path(settings):
    return os.path.join(get_proc_path(settings), 'rootfs')


def get_container_name(settings):
    return '-'.join([
        settings.app_name,
        settings.version,
        settings.config_name,
        settings.release_hash,
        settings.proc_name,
        str(settings.port),
    ])


def get_proc_path(settings):
    return os.path.join(PROCS_ROOT, get_container_name(settings))


def get_build_path(settings):
    """
    Path to which a build should be unpacked.
    """
    return os.path.join(BUILDS_ROOT, '%s-%s' % (settings.app_name,
                                                settings.version))


def get_buildfile_path(settings):
    """
    Path to which a build tarball should be unloaded.
    """

    base = os.path.basename(settings.build_url)
    return os.path.join(BUILDS_ROOT, base)


# FIXME: We should be more explicit about which attributes are allowed and
# required here.  Maybe a namedtuple?
class ProcData(object):
    """
    Given a dict on init, set attributes on self for each dict key/value.
    """
    def __init__(self, dct):
        for k, v in dct.items():
            # Work around earlier versions of proc.yaml that used a different
            # key for proc_name'
            if k == 'proc':
                k = 'proc_name'
            setattr(self, k, v)
