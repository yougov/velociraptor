Containers
==========

Velociraptor apps are deployed to LXC_ containers that give them an isolated
process space and filesystem root.  One way to think of them is "virtual
machines that share a kernel with the host".  Another way to think of them is
"chroot on steroids".

At the time of writing (May 2013) Velociraptor's LXC containers are only
minimally isolated.  Though apps cannot see each other's code or config,
essential system folders are bind-mounted from the host into the container and
shared between apps.  The host's network interface is shared inside the
container.  There are no caps on per proc resource usage (which LXC supports
using Linux cgroups).  As development continues, Velociraptor's containers will
be made more isolated and secure.  For now you should *not* run untrusted 3rd
party code on Velociraptor.

The use of containers enforces the 12 Factor App rules that require state to be
maintained in backing services (databases, caches, etc.) rather than on the
application host.  Any local files written by an app are likely to be deleted
when the app is restarted, and *certain* to be deleted when a different
release of the app is dispatched.

.. _LXC: http://linuxcontainers.org
