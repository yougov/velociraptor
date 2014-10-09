Runners
=======

When you deploy an application with Velociraptor, it runs in a container.
Those containers are set up and launched by a 'runner', which is a small
command line application on the application host.

You can do some neat things using runners:

- Run a container on one host that will uptest a proc on another host (by
  setting the 'host' and 'port' keys in your local proc.yaml appropriately).
- Get a shell on a production host in the exact same environment in which your
  production instance is running.
- Easily start up a local instance of a proc that exactly matches what's
  running production.

The interface between Velociraptor and its runners is specified in terms of
command line arguments and a yaml file. 

A runner is launched with two command line arguments:

1. A command. ('setup', 'run', 'uptest', 'teardown', or 'shell')
2. The path to a proc.yaml file containing all the information necessary to set
   up the container with the application's build and config.

Using the 'setup' command might look like this::

    some_runner setup /home/dave/myproc.yaml

The proc.yaml file
==================

The proc.yaml file contains the following keys:

- port: The network port on which the application should listen, if applicable.
- user: The name of the user account under which the application should be
  run.  The application's files will have their owner set to this user.
- group: The application's files will have their group set to this.
- env: A dictionary of environment variables to be set before launching the
  application.
- settings: A dictionary of config values to be written to settings.yaml inside
  the container.  The location of that file will be passed to the application
  using the APP_SETTINGS_YAML environment variable.
- cmd OR proc_name: If there is a 'cmd' key in proc.yaml, it will be used as
  the command to launch inside the container.  If there is no 'cmd' key, then
  the 'proc_name' key should have an entry like 'web' or 'worker' that points
  to a line in the application's Procfile.
- build_url: The HTTP URL of the build tarball.
- build_md5: Optional.  If supplied, and the runner sees that the build tarball
  has already been downloaded, its md5sum will be checked against build_md5
  from the proc.yaml.

The file doesn't actually have to be named proc.yaml.  It can have any name you
like.

Note: String config values that start with an @ sign and also contain single
quote characters get serialized in a special way by the underlying YAML
library.  For instance, "@How's it going?" gets serialized as
'@How''s it going?'.

Commands
========

Runners support the following commands:

Setup
~~~~~

Example::
  
    some_runner setup /home/dave/myproc.yaml

The ``setup`` command will read the proc.yaml file, download the build (if
necessary), and create necessary scripts, directories and LXC config files for
the container.

If proc.yaml contains a 'cmd' key, this will be written into the startup script
created during setup.  If there is no 'cmd' key, the runner will use the
'proc_name' key to determine which line from the application's Procfile
should be executed.

This command locks the proc.yaml file so other locking runner commands cannot
run on this file at the same time.

Teardown
~~~~~~~~

Example::
  
    some_runner teardown /home/dave/myproc.yaml

The ``teardown`` command should remove the proc folder and related files from the
filesystem.  If the runner has done other changes to the host, such as creating
special network interfaces for the container, it should clean those up too.

Note: It is permissible for teardown to leave a copy of the build tarball in
/apps/builds even after teardown is called.  (There's no way for teardown to
know whether you have other containers based on the same build.)

The teardown command locks the proc.yaml file while running.

Run
~~~

Example::

  some_runner run /home/dave/myproc.yaml

The ``run`` command starts your process inside the container.  The process should
not daemonize.  When the process exists, the container will stop with it.

The run command locks the proc.yaml while running.

Uptest
~~~~~~

Example::
  
  some_runner uptest /home/dave/myproc.yaml

The ``uptest`` command relies on the presence of a proc_name key in proc.yaml.
It looks for any scripts in <app_dir>/uptests/<proc_name> and will execute each
one, passing host and port on the command line (as specified in the uptests
spec).  The host and port settings passed to the uptests will be pulled from
the host and port keys in the proc.yaml.

The results from the uptests will be written to stdout as a JSON array of
objects (one object for each uptest result). The uptest command must *not* emit
any other output besides the JSON results.

Uptests should be run in an environment identical to the proc being tested
(same os, build, settings, environment variables, etc.).

The uptest command does not lock the proc.yaml while running.

Shell
~~~~~

Example::

  some_runner shell /home/dave/myproc.yaml

The ``shell`` command creates and starts a container identical to the one
running for the proc, but starts /bin/bash in it instead of the proc's command.
This is useful for debugging pesky problems that only seem to show up in
production.

The shell command does not lock the proc.yaml while running.

Runner Variants
===============

Velociraptor provides two runner implementations.

vrun_precise
~~~~~~~~~~~~

The ``vrun_precise`` runner is specific to Ubuntu 12.04 (Precise) hosts.  It
creates bind mounts of the host's essential system folders inside the
container.  This matches Velociraptor's original container implementation.

vrun
~~~~

The ``vrun`` runner supports specifying an OS image tarball to be used inside
the container.  It uses the following additional keys in proc.yaml:

- image_name: This should be a filesystem-safe name for the image to be used in
  the container.  Example: ubuntu-core-12.04.3-amd64
- image_url: An http URL from which the image tarball can be downloaded.
- image_md5 (optional): If provided, this checksum will be used to determine
  whether an already-downloaded tarball is correct.  If there's a mismatch, the
  image will be re-downloaded.

Here's a working example of those three proc.yaml lines::

  image_url: http://cdimage.ubuntu.com/ubuntu-core/releases/12.04/release/ubuntu-core-12.04.3-core-amd64.tar.gz
  image_md5: ea978e31902dfbf4fc0dac5863d77988
  image_name: ubuntu-core-12.04.3-amd64

(That Ubuntu core image is only 34MB!)

Image tarballs must be compressed with either gzip or bzip2 compression, and
use the appropriate extension in their filenames.

The ``vrun`` runner uses an overlayfs mount of the unpacked build inside each
container, so the same image can be used by many containers without using any
more disk space.

Other runner implementations may be added in the future, or created as separate
projects.
