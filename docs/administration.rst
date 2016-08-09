Administration
==============

This section provides some guidance on common admininstrative scenarios.

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
