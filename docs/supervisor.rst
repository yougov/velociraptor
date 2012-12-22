=====================
Supervisor is Awesome
=====================

Velociraptor relies heavily on Supervisor_ to manage processes.  It calls
Supervisor's XML RPC interface in order stop and start things, and to report on
which processes are running on which hosts.

===============================
The Velociraptor Event Listener
===============================

Velociraptor includes a Supervisor `event listener`_ plugin to watch for any
changes in process state and put a message on a Redis pubsub when they happen.
The Velociraptor web interface relies on these messages to stay up to date.

You'll need to install the 'raptor' package on each of your hosts and configure
Supervisor to start the 'proc_publisher' event plugin, as shown in
this sample supervisord.conf snippet::

    [eventlistener:proc_publisher]
    command=proc_publisher
    events=PROCESS_STATE,PROCESS_GROUP,TICK_60
    environment=REDIS_URL="redis://localhost:6379/0",HOSTNAME=lucid64

*command*

Supervisor event plugins are configured pretty much like programs, so the
'command' parameter here should point to the proc_publisher script installed by
the raptor package.

*events*

Here you configure the events that Supervisor should send to the plugin.  Set
it as above.

*environment*

Here you set environment variables to be passed in to the event plugin process.
The REDIS_URL variable must be set in order for the plugin to know where to
post events.

The HOSTNAME variable is optional.  If provided, it will be the hostname
included in messages placed on the Redis pubsub.  If not provided, the event
plugin will guess a hostname by calling Python's "socket.getfqdn()" function.
You should set the HOSTNAME variable if the name used in your Velociraptor web
interface isn't the same as the one returned by socket.getfqdn().  If they
don't match, and you don't set HOSTNAME, you'll see duplicate procs on your
dashboard.

=======
Version
=======

Only very recent versions of Supervisor include all the event listener support
that Velociraptor needs.


.. _Supervisor: http://supervisord.org/ 
.. _event listener: http://supervisord.org/events.html
