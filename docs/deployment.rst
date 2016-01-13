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
