Administration
==============

In the process of deploying apps into real-world systems, there
are cases where actions in the UI can lead to surprising outcomes
due to limitations that Velociraptor sets for itself in managing
the systems.

This section provides some guidance on common admininstrative scenarios.

Deploying Workers
-----------------

Workers are not part of a swarm, as they do not bind to a port and must be specifically installed one per host. Also, workers can't be easily deployed without a working worker. Therefore, deploying workers takes special care.

First, swarm another process to the desired version. It could be the beat proc or web proc or another, but it should be using the same configuration as the workers use. After it's built properly, that will have created a release.

Next, manually stop one of your workers. Note the 'config' name of the worker. Then do a manual deploy step (Actions > Deploy), select the release that was just created (should be the first one in the list). Select 'worker' for the proc and give the config the same name as noted previously. Finally, select the same host as the stopped worker and a port of 0 and submit.

The proc should deploy and turn green and start completing tasks. Next, repeat the steps for the remaining workers.

After you're done, you'll have a new set of workers running and the old workers stopped. Additionally, if the last worker deploy worked, that worker would have been deployed using one of the new running workers, so you have some confidence that it's functional, so it's safe now to destroy the old workers.

When a Squad Loses a Host
-------------------------

When a squad unexpectedly loses a host (or hosts), not only do all of the procs on that host cease to function, but also the supervisor will not respond to requests. At the time of this writing, that `causes the dashboard to become unresponsive <https://bitbucket.org/yougov/velociraptor/issues/90>`_... at a time when the administrators desperately need the dashboard.

VR doesn't yet have a UI for deleting members of a squad, so use the Django admin. Navigate manually to /admin/squads, select the affected squad, then check the delete box for each failing host then click save. Repeat for additional squads if necessary.

Dependening on how many hosts died and how much slack you have on the other hosts, you may need to provision replacement hosts. If so, create the hosts using whatever technique you use to provision hosts, and then add those hosts using the VR UI by browsing to /host/add/, entering the FQDN of the host, and selecting the target squad in which it should be added. Repeat for each supplemental host needed.

Now your environment should be responsive and ready to recover your failed procs. Since VR does not keep a record of which procs are offline, your best option is to dispatch all swarms in the affected squad or squads. Any swarms that are already complete will be quickly fulfilled, and only those not matching the running configuration will be re-deployed and re-routed.

To identify the relevant swarms, there's no UI that will accomplish this for you. You must go to the database, find the relevant squad, and then query for swarms pointing to that squad. If that's too much trouble, you can consider simply dispatching all swarms, which you can list with the CLI::

    $ vr.cli list-swarms '.*'
    swarm1-config1-runner
    swarm2-config2-runner
    ...

Once you have the list of swarms, you can readily dispatch each of those using the same version that was last indicated::

    $ export RELEVANT_SWARM_PATTERN="swarm1-config1-runner|swarm2-config2-runner|..."
    $ vr.cli swarm "$RELEVANT_SWARM_PATTERN" -

Important is the last '-' character, which is the version to dispatch. The dash simply indicates use the current version.

The CLI will then dispatch each of the indicated swarms, getting all the procs back to production levels.

Proc Supervisor
---------------

Velociraptor delegates the process supervision to Supervisor. As
a result, procs in the UI may not have been deployed by
VR, but could have been deployed manually. Regardless of how
a proc came to exist in supervisor, it is displayed in the UI.

Defunct Procs
-------------

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
