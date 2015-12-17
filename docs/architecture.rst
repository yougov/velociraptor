============
Architecture
============

Velociraptor (VR) seeks to create repeatable deployments by technical and
non-technical users across a suite of languages, providing the
service commonly knows as Platform as a Service or PaaS.

VR is inspired by `Heroku <https://heroku.com>`_ and in particular
the `12-factor methodology <http://12factor.net>`_. VR supports
the use of buildpacks for flexible, pluggable building of source
code into apps suitable for deployment into Linux containers (lxc).

-------
Caveats
-------

In the process of deploying apps into real-world systems, there
are cases where actions in the UI can lead to surprising outcomes
due to limitations that Velociraptor sets for itself in managing
the systems.

Proc Supervisor
~~~~~~~~~~~~~~~

Velociraptor delegates the process supervision to Supervisor. As
a result, procs in the UI may not have been deployed by
VR, but could have been deployed manually. Regardless of how
a proc came to exist in supervisor, it is displayed in the UI.

Defunct Procs
~~~~~~~~~~~~~

Although Velociraptor will tear down procs within the same swarm
when they are no longer needed for that swarm, if the definition
of the swarm changes, Velociraptor will no longer recognize the
extant procs from a previous manifestation of a particular swarm.

For example, if one has a swarm for MyApp, but then changes
the Application to be MyAppNG, Velociraptor will deploy new procs
to service a swarm called MyAppNG-{ver}-{config}, but it will
do nothing to eliminate the MyApp-{ver}-{config}. It will, if
configured, update the routing to point to the new app, giving
the desired behavior, i.e. that MyAppNG is the exposed service,
but the rogue procs will continue to run.

It is unclear at this time if those rogue procs are recognized as
consuming a port in Velociraptor's port accounting.

This condition can happen when mutating any of the following
Swarm fields:

  - App
  - Proc name
  - Config name
  - Squad

Therefore, to avoid leaving rogue procs lying around, it is
recommended that one of the following techniques be
followed to clean up the orphaned procs:

  - Manually delete them using the UI or CLI.
  - Create another swarm matching the original and
    dispatch it with a size of 0.
  - Before making the change, first dispatch the
    swarm with a size of 0 (this will result in downtime).
  - Re-use the mutated swarm by mutating it back
    but also clear the routing fields (so that routing is
    not affected) and with a size of 0. Then, restore
    the desired settings in the swarm.

