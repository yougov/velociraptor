Volumes
=======

Velociraptor's volumes features allows to to specify one or more directories on
the host to be mounted inside the container.  

Caution
~~~~~~~~

The volumes feature is a departure from Velociraptor's normal requirement that
applications be completely stateless (i.e. `12 Factor`_-compliant).  With
volumes, applications may maintain some state between deployments by reading
from and writing to persistent files on the local disk.

Configuration
~~~~~~~~~~~~~

Volumes are specified in the user interface by entering YAML configuration into
the Swarm or Release forms.  In both cases, the YAML should be a list of host
dir, mountpoint pairs::

 - [/var/data, /data]

In that example, the host's /var/data folder will be mounted inside the
application's container at /data.

You may specify multiple volumes for a container::

 - [/var/data, /data]
 - [/blahblah/cache, /cache]

Because YAML supports multiple ways of encoding the same structure, you are
likely to see notation different from the above when viewing volumes in the UI.
This format is equivalent to the above::

 - - /var/data
   - /data
 - - /blahblah/cache
   - /cache

Permissions
~~~~~~~~~~~

Volumes are implemented using `bind mounts`_ written into the proc's LXC
container configuration.  They will *not* automatically modify any permissions on
the files in the volume in order to make them readable or writable by your
application.  It is up to you to ensure that the permissions are appropriately
set, and then use the 'Run as' field in the Swarm and Release forms to make
your application run as the right user.

.. _12 Factor: http://12factor.net/
.. _bind mounts: http://docs.1h.com/Bind_mounts
