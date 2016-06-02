Deploying Velociraptor
======================

This page serves as a placeholder for instructions and advice on
deploying Velociraptor in a production environment.

Setting Memory Limits
---------------------

In order to support the memory limits on containers, the host
kernel must be configured with one or both of the following
command-line parameters:

    swapaccount=1
    cgroup_enable=memory

Please update this document if you can provide clarification on
which parameters are actually required and how to specify those
parameters.

Monitoring with Flower
----------------------

As Velociraptor uses celery queues to manage its tasks, it's
often useful to have a tool for monitoring them. The
`Flower project <http://flower.readthedocs.io/en/latest/>`_
implements one such tool.

To deploy it against your broker, add a proc to your VR Procfile
like so::

    flower: python -m vr.server.manage celery flower --broker=$BROKER --port=$PORT

Add the flower dependency in your requirements.txt (alongside
other VR dependencies)::

    Flower =>0.9, <1

And deploy that proc using VR. You'll then have a web service
configured to monitor Celery.
