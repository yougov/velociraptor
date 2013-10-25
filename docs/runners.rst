Runners
=======

When you deploy an application with Velociraptor, it runs in a container.
Those containers are set up and launched by a 'runner', which is a small
command link application on the application host.

The interface between Velociraptor and its runners is specified in terms of
command line arguments and a yaml file.  This allows different runners to take
different approaches to setting up the application container.  Some might
bind-mount in the system's essential folders to create the environment.  Others
might unpack a whole OS image tarball.

A runner is launched with two command line arguments:
1. A command. ('setup', 'run', 'uptest', 'teardown', or 'shell')
2. The path to a proc.yaml file containing all the information necessary to set
   up the container with the application's build and config.

Using the 'setup' command might look like this::

    some_runner setup /home/dave/myproc.yaml

The proc.yaml file must contain the following keys:
- port: The network port on which the application should listen, if applicable.
- user: The name of the user account under which the application should be
  run.  The
- group: The name
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

