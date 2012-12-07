=========
Balancers
=========

Velociraptor has the ability keep your load balancer configuration up to date
as nodes come and go on different hosts and ports.  This is done through
Velociraptor's "balancer" interface.  When you define a Swarm you have the
option to pick a pool name and balancer for routing traffic to that swarm.  The
list of available balancers is configured in the Django settings::

  BALANCERS = {
      'default': {
          'BACKEND': 'deployment.balancer.dummy.DummyBalancer',
      }
  }



In the above example, a balancer named "default" is configured, by setting the
BACKEND parameter to the dotted-path location of the DummyBalancer class in the
Python path.  The no-op "dummy" balancer doesn't actually route anything.  It
just stubs out the balancer methods for running in tests and development.
Besides the dummy balancer, there are several real balancer backends available.
The rest of the configuration examples use YAML, as you would use if you deploy
Velociraptor itself from Velociraptor.

Nginx
-----

The nginx_ balancer backend can be configured like so::

  BALANCERS:
    my_nginx_balancer:
      BACKEND: deployment.balancer.nginx.NginxBalancer 
      user: some_user_with_sudo
      password: some_password
      include_dir: /etc/nginx/sites-enabled/
      reload_cmd: /etc/init.d/nginx reload
      tmpdir: /tmp
      hosts:
      - frontend1.mydomain.com
      - frontend2.mydomain.com

One by one, here's what those config values mean:

- my_nginx_balancer: An artbitrary name for this balancer.  It will be saved
  with swarm records in the database.  If you change it later, you'll have to
  update those records with the new name.
- user: The username to be used by Velociraptor when SSHing to the nginx hosts.
- password: The password to be used by Velociraptor when SSHing to the nginx
  hosts.
- include_dir: The path to a folder that nginx has been configured to use for
  config includes.  The balancer backend will write files there to define
  pools.  It's set to the Ubuntu location by default, so if you're on that OS
  you can omit this setting.
- reload_cmd: The command to be used to tell nginx to reload its config.  By
  default this uses the command for the Ubuntu init script.
- tmpdir: A place to put temporary files.  Defaults to /tmp, so you can omit it
  if you don't need to customize it.
- hosts: The list of nginx hosts whose config should be updated.

Varnish
-------

Like the nginx balancer, the Varnish_ balancer connects to hosts over SSH in
order to read/write files and run commands.  It shares a common base class with
the nginx balancer, so its config is very similar::

  BALANCERS:
    my_varnish_balancer:
      BACKEND: deployment.balancer.varnish.VarnishBalancer 
      user: some_user_with_sudo
      password: some_password
      include_dir: /etc/varnish/
      reload_cmd: /etc/init.d/varnish reload
      tmpdir: /tmp
      hosts:
      - cache1.mydomain.com
      - cache2.mydomain.com

It also uses Ubuntu defaults for include_dir and reload_cmd.

Stingray/ZXTM
-------------

The balancer backend for Stingray_ (fka ZXTM) connects over SOAP rather than
using SSH, so its config looks different::

    BALANCERS:
      my_stingray_balancer:
        BACKEND: deployment.balancer.zxtm.ZXTMBalancer
        URL: https://traffic.yougov.local:9090/soap
        USER: api_user
        PASSWORD: api_user_password
        POOL_PREFIX: vr-

Those parameters are:

- URL: The URL to the SOAP interface.
- USER: username to be used for the SOAP connection.
- PASSWORD: password to be used for the SOAP connection.
- POOL_PREFIX: All pools created by Velociraptor will be prefixed with this
  name.  This is useful if you have both automatically- and manually-created
  pools.

Using Multiple Balancers:
-------------------------

You can use multiple balancers by having multiple entries in the BALANCERS
setting::

  BALANCERS:
    my_varnish_balancer:
      BACKEND: deployment.balancer.varnish.VarnishBalancer 
      user: some_user_with_sudo
      password: some_password
      hosts:
      - varnish.mydomain.com
    my_nginx_balancer:
      BACKEND: deployment.balancer.nginx.NginxBalancer 
      user: some_user_with_sudo
      password: some_password
      hosts:
      - nginx.mydomain.com

The above example includes both an nginx and varnish balancer.  (It also omits
the settings that have Ubuntu defaults, so if you're not on Ubuntu you'll have
to fill those in.)

Routing Rules and Other Intentional Omissions
---------------------------------------------

Load balancers/traffic managers have an eclectic and bewildering array of
features, and wildly different interfaces and config languages for driving
them.  Velociraptor does *not* attempt to provide an abstraction over all those
features.  The balancer interface is concerned solely with creating and
updating pools.  It's up to you to add rules telling your load balancer which
hostnames/ports/paths/etc should map to which pools.

Concurrency Caveats
-------------------

When you add nodes using one of the SSH-based balancers (nginx and Varnish), it
will do the following:

1) Get the current list of nodes by reading the remote balancer's config.
2) Add the new nodes to that list.
3) Write a new config file (or files).
4) Tell the remote service to reload its config.

If two processes are both making changes at the same time, there's opportunity
for the first one's changes to be overwritten by the second's.  

In the nginx balancer, this risk is mitigated somewhat by use of a separate
file for each pool.  So you'll only have problems if two workers are both
trying to update the same pool at the same time.

Varnish, however, does not support a glob-style include of all files in a
directory as nginx does, so the Varnish balancer maintains a pools.vcl file
with include directives for all of the pool-specific files.  The pools.vcl file
is updated only when new pools are created.  So there is additional risk of
overwritten config with the Varnish balancer if two Velociraptor workers are
trying to create new pools at the same time.  (This is *probably* an extremely
rare occurence, but it will depend on the size of your Velociraptor
installation.)

Additionally, if you have multiple nginx or Varnish instances configured for a
balancer, there will be a few seconds of lag between when the first and last
one get their new config.  (SSHing and reading/writing files takes time.)

The ZXTM/Stingray balancer does not suffer from the same concurrency risks as
the SSH-based balancers, because the underlying SOAP API provides atomic
methods for add_nodes and delete_nodes.

Creating New Balancer Backends
------------------------------

A balancer is a Python class that provides the following interface:

- On init, it accepts a "config" dictionary containing all of the config
  parameters it needs in order to function.
- A get_nodes method, which accepts a single string argument for the name of
  the pool, and returns a list of nodes, which are strings in the form
  "hostname:port".  If the pool does not exist, this method should return an
  empty list.
- An add_nodes method that accepts two arguments: 1) A pool name, and 2) a list
  of nodes.  If the pool does not exist, it should be automatically created by
  this function.
- A delete_nodes method that accepts two arguments: 1) A pool name, and 2) a
  list of nodes.  This function should return successfully even if the pool
  or one of the nodes does not exist.

Here's a hand-wavy hypothetical example::

    # the abstract base class in the raptor lib doesn't actually provide any
    # behavior but does help ensure you've implemented the right methods.

    from raptor.balancer import Balancer

    class ImaginaryBalancer(Balancer):
        def __init__(self, config):
            self.config = config

        def get_nodes(self, pool_name):
            try:
                pool = go_get_a_pool(pool_name)
                return pool.nodes
            except PoolDoesNotExist:
                return []

        def add_nodes(self, pool_name, nodes):
            try:
                pool = go_get_a_pool(pool_name)
                pool.add_nodes(nodes)
            except PoolDoesNotExist:
                go_create_a_pool(pool_name, nodes)

        def delete_nodes(self, pool_name, nodes):
            try:
                pool = go_get_a_pool(pool_name)
                pool.delete_nodes(nodes)
            except PoolDoesNotExist:
                pass


Velociraptor doesn't yet have balancer backends for Apache or HAProxy.  It
probably should!  Patches are welcome if you'd like to submit an additional
balancer backend.

.. _nginx: http://nginx.org/
.. _Varnish: https://www.varnish-cache.org/
.. _Stingray: http://www.riverbed.com/us/products/stingray/stingray_tm.php
