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
Vagrantfile.  This requires having VirtualBox_ and Vagrant_ installed.  Once
they're installed, type this in the repo's root::

    vagrant up

Now go make a sandwich while you wait for the lucid64 VM image to download
(it's about 250MB).

Installation of system-level dependencies inside the VM is done automatically
using Vagrant's Puppet provisioner.  This includes some normal apt packages,
(RabbitMQ), some from Ubuntu PPAs (Postgres 9.1 and Python 2.7), and some
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
    pip install -r requirements.txt -i http://cheese.yougov.net

Database
~~~~~~~~

There is a dbsetup.sql file included that contains commands for creating the
Postgres database used by Velociraptor::

    psql -U postgres < dbsetup.sql

Once your database is created, you'll need to create the tables::

    cd /vagrant/project
    ./manage.py syncdb
    ./manage.py migrate

Some of the tables are managed by South_ instead of syncdb.  To make sure
they're created, you need to run this too::

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

Editing Code
~~~~~~~~~~~~

Running the code inside a VM does not mean that you need to do your editing
there.  Since the project repo is mounted inside the VM, you can do your
editing on the outside with your regular tools, and the code running on the
inside will stay in sync.

.. _Twelve Factor App: http://www.12factor.net/
.. _Vagrant: http://vagrantup.com/docs/getting-started/index.html
.. _VirtualBox: http://www.virtualbox.org/wiki/Downloads
.. _Foreman: http://ddollar.github.com/foreman/
.. _Virtualenvwrapper: http://www.doughellmann.com/docs/virtualenvwrapper/
.. _South: http://south.aeracode.org/
.. _Celery: http://celeryproject.org/
