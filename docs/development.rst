Development
===========

VM
~~

The smoothest way to get running is to start up a VM with the included
Vagrantfile.  This requires having VirtualBox_ and Vagrant_ installed.
Go do that now.

You'll need a local clone of the Velociraptor repo::

    hg clone https://bitbucket.org/yougov/velociraptor

Now enter the velociraptor folder and launch vagrant::

    cd velociraptor
    vagrant up

Now go make a sandwich while you wait for the Ubuntu Trusty VM image to
download (about 430MB).

Installation of system-level dependencies inside the VM is done automatically
using Vagrant's Puppet provisioner.  This includes some normal apt packages,
(curl, Vim, Postgres), and some installed with pip (Mercurial and Virtualenv).
You can see the Puppet manifest at puppet/manifests/vr.pp.

The first time you 'vagrant up', the Puppet provisioning could take about
5 minutes.  It will be faster on later startups, since most packages will
already be installed.

Once the image is all downloaded and Puppet has run, log in with::

    vagrant ssh

You're now inside your new Vagrant VM!  The Velociraptor repo will be at
/vagrant.  Now make a Python virtualenv for yourself.  It will use Python 2.7
by default.  Virtualenvwrapper_ is pre-installed to make this extra easy::

    mkvirtualenv velo

Python Dependencies
~~~~~~~~~~~~~~~~~~~

Velociraptor contains a dev_requirements.txt file listing its dev-time Python
dependencies.  You can install the dependencies with this::

    cd /vagrant
    pip install -r dev_requirements.txt

Database
~~~~~~~~

There is a dbsetup.sql file included that contains commands for creating the
Postgres database used by Velociraptor::

    psql -U postgres -f dbsetup.sql

Once your database is created, you'll need to create the tables.  (Please
forgive the deeply nested folders; I know it's tedious, but it's the cost of
using several namespaced Python packages in the same repo)::

    server/vr/server/manage.py syncdb --noinput
    server/vr/server/manage.py migrate

The schema is created with an initial user ``admin`` with password ``password``.

As Velociraptor is developed and the DB schema changes, you can run
`./manage.py migrate` again to get your local DB schema in sync with the code.

Dev Server
~~~~~~~~~~

The Velociraptor server is composed of three processes:

1. The main Django web service.
2. A Celery_ daemon that starts and controls one or more workers.
3. A 'celerybeat' process that puts maintenance jobs on the Celery queue at
   preconfigured times.

There is a Procfile included with Velociraptor that can be used to run a
development environment with these processes. You can use Foreman_ to
read the Procfile and start the processes it lists::

    foreman start -f Procfile.dev

That will start the Django dev server on port 8000, the Celery workers, and the
celerybeat process.

Now open your web browser and type in http://localhost:8000.  You should see
Velociraptor.  (The Vagrantfile is configured to forward ports 8000, 9001, and
5000-5009 to the VM.  If you need these ports back for other development, you
can stop your Vagrant VM with a `vagrant halt`.)

Add Metadata
~~~~~~~~~~~~

Buildpacks
----------

In order to build and deploy your apps, Velociraptor needs to be told where
they are and how to build them.  The 'how to build them' part is done with
Heroku buildpacks.  Go to http://localhost:8000/buildpack/add/
in your browser in order to add a buildpack.  You will need to enter the git
(or mercurial) repository URL, as well as an integer for the 'order'.  See the
`Heroku buildpack documentation`_ to understand more about how buildpacks work
and why order matters.  For now, just add a single buildpack, and set its order
to '0'.  A good one to start is the `NodeJS buildpack
<https://github.com/heroku/heroku-buildpack-nodejs.git>`_.

Squads and Hosts
----------------

In order for Velociraptor to know where to deploy an application, it requires
some hostnames.  Velociraptor does load balanced deployments
across a group of hosts called a "Squad".  Go to
http://localhost:8000/squad/add/ to create a new squad.  Call it whatever you
like (I suggest 'local').  Squad names must be
unique.  Then add a host; go to http://localhost:8000/host/add/ and
give the squad a host named 'vr-master', which is the hostname of the Vagrant
VM itself.

Stacks and Images
-----------------

Velociraptor uses a container based system for isolating the execution
environments of each application.

A "legacy" stack is provided but deprecated.

Instead, create a trusty stack. Use the base trusty image per docs.
http://cdn.yougov.com/build/ubuntu_trusty_pamfix.tar.gz

Provision the stack with the 'provision.sh' file from the
Velociraptor repository. You must also provide name and description.
Use "trusty" for both.

The provisioning script takes some time as it needs to download, expand,
and mount the base image, run the provisioning script in a container
for that image, collect the image back into an archive, and upload
the image to the Velociraptor image repository.

Watch the "worker" log for progress and wait for a green cube icon in
the UI. The process takes most of 20 minutes.

Apps
----

Now tell Velociraptor about your code!  Go to http://localhost:8000/app/add/
and give the name, repo url, and repo type (git or hg) of your application.  If
you don't have one around, try the vr_node_example_ app.  The name you give to
your app should have only letters, numbers, and underscores (no dashes or
spaces).

You can leave the 'buildpack' field blank.  Velociraptor will use the
buildpacks' built-in 'detect' feature to determine which buildpack to use on
your app.

Select "trusty" for the stack.

Swarms
------

Swarms are where Velociraptor all comes together.  A swarm is a group of
processes all running the same code and config, and load balanced across one or
more hosts.  Go to http://localhost:8000/swarm/ to create yours.  Here's what
all the form fields mean:

- App: Select your app from this drop down.
- Tag: This is where you set the version of the code that Velociraptor should
  check out and build.  You can use almost any tag, branch name, bookmark, or
  revision hash from your version control system (any valid 'git
  checkout' or 'hg update' target), as long as it does not contain invalid
  characters for use in file names/directory names (most notably, /).
  Use 'v5' for the vr_node_example.
- Proc name: The name of the proc that you want to run in this swarm (from the
  Procfile).  Type in 'web' for vr_node_example.
- Config Name: This is a short name like 'prod' or 'europe' to distinguish
  between deployments of the same app. Must be filesystem-safe, with no dashes
  or spaces.  Use 'demo' here for vr_node_example.
- Squad: Here you declare which group of hosts this swarm should run on.  If
  you set up the squad as indicated earlier in this walkthrough, you should be
  able to select 'local' here.
- Size: The number of procs to put in the swarm.  Try 2 for now.
- Config YAML: Here you can enter optional YAML text that will be written to
  the remote host when your app is deployed.  Your app can find the location of
  this YAML file from the APP_SETTINGS_YAML environment variable.
- Env YAML: Here you can enter YAML text to specify additional environment
  variables to be passed in to your app.
- Pool: If your app accepts requests over a network, you can use this "pool"
  field to tell your load balancer what name to use for the routing pool.  By
  default Velociraptor talks only to an in memory stub balancer called "Dummy".
  For the walkthrough, leave this field blank.
  To configure a real load balancer, see docs/balancers.rst in the Velociraptor
  repo.  Velociraptor supports nginx_, Varnish_, and Stingray_ load balancers.
  This interface is pluggable, so you can also create your own.
- Balancer: Here you select which balancer should be told to route traffic to
  your swarm.  For the walkthrough, leave this field blank.

Now click Swarm.  Velociraptor will start a series of worker tasks to check out
the buildpack, check out your code, download the image, compile your code
in the image, save the resulting
build, push it out to the hosts in the squad along with any config you've
specified, and launch the code within the stack image.  The Swarm Flow diagram
in the docs folder illustrates the process.


Tests
~~~~~

Run the tests with py.test from the root of the repo after installing
the dev requirements::

    cd /vagrant
    pip install -r dev_requirements.txt
    py.test

The tests will automatically set up and use separate databases from the default
development ones.

While developing, you might want to speed up tests by skipping the database
creation (and just re-using the database from the last run).  You can do so
like this::

    py.test --nodb

This should be safe as long as we keep using randomly-generated usernames,
etc., inside tests.

Editing Code
~~~~~~~~~~~~

Running the code inside a VM does not mean that you need to do your editing
there.  Since the project repo is mounted inside the VM, you can do your
editing on the outside with your regular tools, and the code running on the
inside will stay in sync.

Structure
~~~~~~~~~

Velociraptor's code is divided between the parts that are Django-specific (the
web and worker processes), and the supporting library that is not.

The Django parts are inside the 'vr' folder.  The non-Django parts are in
the 'libraptor' folder.  This may be moved into a separate repository in the
future.

Some dependent projects are hosted in separate repos:

 - `vr.events`_ <https://bitbucket.org/yougov/vr.events>
 - `vr.cli`_ <https://bitbucket.org/yougov/vr.cli>

UI
~~

All frontend interfaces rely on a 'VR' javascript object defined in
deployment/static/js/vr.js.  Individual pages add their own sub-namespaces like
VR.Dash and VR.Squad, using vrdash.js and vrsquad.js, for example.

Velociraptor uses goatee.js_ templates (a Django-friendly fork of
mustache.js_). They are defined as HTML script blocks with type "text/goatee".

Velociraptor makes liberal use of jQuery_, Backbone_, and Underscore_.


Repositories (and Subrepositories)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Velociraptor is a suite of projects in the `vr` namespace. Each of these
projects are a separate repository, linked by the parent repository
https://bitbucket.org/yougov/velociraptor.

Here are some hints for developing with subrepositories.

Getting the latest code
-----------------------

Generally speaking, the parent repository should have up-to-date
references to the subrepositories, meaning that if you simply
``hg pull -u``, you will get those references and Mercurial will
automatically pull the latest code for the subrepositories.

However, sometimes code is pushed to the child repositories without
updating the parent repository. If this is the case, you can
``hg pull -u`` in each of the individual child repositories or use
``onsub``.

Using onsub
-----------

Mercurial supports the `onsub extension
<https://www.mercurial-scm.org/wiki/OnsubExtension>`_ for easily
invoking an operation across subrepositories. After installing
that extension, grabbing the latest code for the subrepositories
is as simple as invoking ``hg onsub 'hg pull -u'``.

Committing updated references
-----------------------------

After committing new changes to any of the subrepositories or
pulling changes that weren't previously referenced by the parent
repository, you can update the references in the parent repository
by simply committing in that repo::

    $ hg ci -m "Updating child repository references"

That will update the .hgsubstate for each of the subrepositories
to match whatever version is currently updated for the working copy::

    $ hg id -R server
    f341811ac9a2 tip
    $ grep server .hgsubstate
    f341811ac9a229aaf0b053c9f957f53caa87577f server

Push those changes so that others who pull and update the
velociraptor repo will get the updated child repos as well. Note
that when you push the parent repo, Mercurial will push the
child repos too in order to ensure that the referenced repo versions
will be available to others.


.. _Vagrant: http://vagrantup.com/v1/docs/getting-started/index.html
.. _VirtualBox: http://www.virtualbox.org/wiki/Downloads
.. _Foreman: http://ddollar.github.com/foreman/
.. _Virtualenvwrapper: http://www.doughellmann.com/docs/virtualenvwrapper/
.. _South: http://south.aeracode.org/
.. _Celery: http://celeryproject.org/
.. _jQuery: http://jquery.com/
.. _Backbone: http://backbonejs.org/
.. _Underscore: http://underscorejs.org/
.. _vr_node_example: https://bitbucket.org/btubbs/vr_node_example
.. _nginx: http://wiki.nginx.org/Main
.. _Varnish: https://www.varnish-cache.org/
.. _Stingray: http://www.riverbed.com/products-solutions/products/application-delivery-stingray/
.. _Heroku buildpack documentation: https://devcenter.heroku.com/articles/buildpacks
.. _goatee.js: https://github.com/btubbs/goatee.js
.. _mustache.js: https://github.com/janl/mustache.js
.. _vr.cli: https://bitbucket.org/yougov/vr.cli
.. _vr.events: https://bitbucket.org/yougov/vr.events
