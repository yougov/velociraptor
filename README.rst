Meet Velociraptor
=================

Velociraptor is a Django- and Celery-powered web application for building and
deploying software services.  It is *very* opinionated about how this should be
done, adhering (with one or two exceptions) to the `Twelve Factor App`_
methodology.

Development
===========

VM
~~

The smoothest way to get running is to start up a VM with the included
Vagrantfile.  This requires having VirtualBox_ and Vagrant_ installed.
Go do that now.

You'll also need a local Mercurial workspace containing the
G/velociraptor/ directory tree::

    hg clone https://bitbucket.org/yougov/velociraptor

Now enter the velociraptor tree and launch vagrant::

    cd velociraptor
    vagrant up

Now go make a sandwich while you wait for the precise64 VM image to download
(it's about 250MB).

Installation of system-level dependencies inside the VM is done automatically
using Vagrant's Puppet provisioner.  This includes some normal apt packages,
(curl, Vim), some from Ubuntu PPAs (Postgres 9.1 and Python 2.7), and some
installed with pip (Mercurial and Virtualenv).  You can see the Puppet manifest
at manifests/yhost.pp.

The first time you 'vagrant up', the Puppet provisioning could take about
5 minutes.  It will be faster on later startups, since most packages will
already be installed.

Once the image is all downloaded and Puppet has done its thing, type this::

    vagrant ssh

You're now inside your new Vagrant VM!.  The Velociraptor repo will be at
/vagrant.  Now make a Python virtualenv for yourself.  It will use Python 2.7
by default.  Virtualenvwrapper_ is pre-installed to make this extra easy::

    mkvirtualenv velo

Python Dependencies
~~~~~~~~~~~~~~~~~~~

Velociraptor contains a requirements.txt file listing its Python dependencies.
You can install the dependencies with this::

    cd /vagrant
    pip install -r requirements.txt

Database
~~~~~~~~

There is a dbsetup.sql file included that contains commands for creating the
Postgres database used by Velociraptor::

    psql -U postgres -f dbsetup.sql

Once your database is created, you'll need to create the tables::

    cd /vagrant/project
    ./manage.py syncdb
    ./manage.py migrate

As Velociraptor is developed and the DB schema changes, you can run
`./manage.py migrate` again to get your local DB schema in sync with the code.

Dev Server
~~~~~~~~~~

Velociraptor is composed of two main processes:

1. The main Django web service.
2. A Celery_ daemon that starts and controls one or more workers.

There is a Procfile included with Velociraptor that can be used to run a
development environment with both of these processes. You can use Foreman_ to
read the Procfile and start the processes it lists::

    cd /vagrant
    foreman start -f Procfile.dev

That will start the Django dev server on port 8000 and the Celery daemon. 

Now open your web browser and type in http://localhost:8000.  You should see
Velociraptor.  (The Vagrantfile is configured to forward ports 8000-8009 to the
VM.  If you need these ports back for other development, you can stop your
Vagrant VM with a `vagrant halt`, run from the same location where you ran
`vagrant up`.)

Add Metadata
~~~~~~~~~~~~

Buildpacks
----------

In order to build and deploy your apps, Velociraptor needs to be told where
they are and how to build them.  The 'how to build them' part is done with
Heroku buildpacks.  Go to http://localhost:8000/admin/deployment/buildpack/add/
in your browser in order to add a buildpack.  You will need to enter the git
(or mercurial) repository URL, as well as an integer for the 'order'.  See the
`Heroku buildpack documentation`_ to understand more about how buildpacks work
and why order matters.  For now, just add a single buildpack, and set its order
to '0'.  The NodeJS buildpack at
https://github.com/heroku/heroku-buildpack-nodejs.git is a good one to start
with.

Squads and Hosts
----------------
In order to know where to deploy your application, you'll need to give
Velociraptor some hostnames.  Velociraptor does load balanced deployments
across a group of hosts, which it calls a "Squad".  Go to
http://localhost:8000/admin/deployment/squad/add/ to create a new squad.  Call
it whatever you like (I call my development squad 'local'.  Squad names must be
unique.  Give the squad a single host named 'precise64', which is the hostname
of the Vagrant VM itself.

Apps and Recipes
----------------


Tests
~~~~~

Run the tests with py.test from the root of the repo.  You can install
any test dependencies using the test_requirements.txt::

    cd /vagrant
    pip install -r test_requirements.txt

It will automatically set up and use separate databases from the
default development ones::

    cd /vagrant
    py.test

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

Velociraptor is a Django project, and organized as such.  Most of the code is
in the 'deployment' app inside the 'project'.  The 'deployment' app contains
models.py, views.py, etc.  The Celery tasks that handle actual deployment
actions are in project/deployment/tasks.py.

UI
~~

All frontend interfaces rely on a 'VR' javascript object defined in
deployment/static/js/vr.js.  Individual pages add their own sub-namespaces like
VR.Dash and VR.Squad, using vrdash.js and vrsquad.js, for example.

Velociraptor uses goatee.js_ templates (a Django-friendly fork of
mustache.js_). They are defined as HTML script blocks with type "text/goatee".

Velociraptor makes liberal use of jQuery_, Backbone_, and Underscore_.

.. _Twelve Factor App: http://www.12factor.net/
.. _Vagrant: http://vagrantup.com/v1/docs/getting-started/index.html
.. _VirtualBox: http://www.virtualbox.org/wiki/Downloads
.. _Foreman: http://ddollar.github.com/foreman/
.. _Virtualenvwrapper: http://www.doughellmann.com/docs/virtualenvwrapper/
.. _South: http://south.aeracode.org/
.. _Celery: http://celeryproject.org/
.. _goatee.js: https://github.com/btubbs/goatee.js
.. _mustache.js: https://github.com/janl/mustache.js
.. _jQuery: http://jquery.com/
.. _Backbone: http://backbonejs.org/
.. _Underscore: http://underscorejs.org/
