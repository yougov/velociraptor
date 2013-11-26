"""
Constants and functions for determining where Velociraptor puts things at
deploy time.  All of the get_* functions accept a ProcData object, which is is
built from a dict parsed out of a proc.yaml file.
"""
import os

# Imported here just to satisfy legacy versions of vr.runners that used to grab
# it here.
from vr.common.models import ProcData

VR_ROOT = '/apps'
BUILDS_ROOT = VR_ROOT + '/builds'
PROCS_ROOT = VR_ROOT + '/procs'
RELEASES_ROOT = VR_ROOT + '/releases'


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


def get_app_path(settings):
    """
    Path to which a build should be unpacked.
    """
    # These days, we unpack a separate copy of the build for each proc on the
    # host.  This is the easiest way around different instances possibly
    # running as different users, while still being able to write .pyc files in
    # there (for example).  In practice, Velociraptor wouldn't get much
    # disk/memory savings from having multiple procs pointing at the same
    # underlying files anyway, because VR tries hard to distribute instances of
    # the same app across different hosts.
    return os.path.join(get_container_path(settings), 'app')


def get_buildfile_path(settings):
    """
    Path to which a build tarball should be downloaded.
    """
    base = os.path.basename(settings.build_url)
    return os.path.join(BUILDS_ROOT, base)

