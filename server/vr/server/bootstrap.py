"""
This is a fabfile for installing Velociraptor system components onto one or
more hosts. This file must remain importable and runnable without anything
Django-specific getting dragged in.  (No Django models or settings.)

There are three components that this fabfile can install:

vr.agent.  This is the Supervisor event listener and RPC plugin.  It needs to
be installed on all hosts that will run procs.  Installation example:

    fab -f bootstrap.py install_agent -H host1,host2

vr.runners.  This provides the vrun_precise and vrun commands.  It also needs
to be installed on all hosts.  Installation example:

    fab -f bootstrap.py install_runners -H host1,host2

vr.builder.  This supports building applications in temporary containers.
It needs to be installed only on hosts that run a Velociraptor 'worker'
proc.  Installation example:

    fab -f bootstrap.py install_builder -H host1,host2

These commands will connect to the hosts over SSH and use sudo to install the
packages.  If you need to connect as a different user, add -u <username>
arguments to the command.

All of the installer commands accept two optional arguments:
    - Version of the package to install.
    - Python "cheeseshop" from which the packages should be downloaded.

Installing with those additional arguments looks like this:

    fab -f bootstrap.py install_runners:0.0.13,http://mycustomcheeseshop.net -H host1,host2

"""
from fabric.api import task, sudo


@task
def install_package(package, version=None, cheeseshop=None):
    """
    Install a package into the host's system Python.  Optionally specify a
    version and a cheeseshop URL.
    """
    cmd = 'pip install ' + package
    if version:
        cmd += '==' + version

    if cheeseshop:
        cmd += ' -i ' + cheeseshop
    sudo(cmd)


@task
def install_runners(*args, **kwargs):
    install_package('vr.runners', *args, **kwargs)


@task
def install_builder(*args, **kwargs):
    install_package('vr.builder', *args, **kwargs)


@task
def install_agent(*args, **kwargs):
    install_package('vr.agent', *args, **kwargs)
