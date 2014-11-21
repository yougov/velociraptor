Stacks
======

Velociraptor's concept of a "stack" is more or less the same as `Heroku's`_::

    A stack is a complete deployment environment including the base operating
    system, the language runtime and associated libraries. As a result,
    different stacks support different runtime environments.

OS Images are to Stacks as Builds are to Apps
=============================================

Unlike Heroku, Velociraptor lets you create your own stacks, and provides tools
to make it fairly simple.  When using the Velociraptor UI, you can select
Platform -> Stacks from the menu.  To create a new stack, you will need to
provide the URL for a base image tarball and a script to run inside the base
image to install the things you need.  Put those pieces of information in the
form and click "Save and Build".  Velociraptor will tell one of its workers to
do the following:

1. Download your base image and unzip it.
2. Start a container with your base image mounted in read/write mode.
3. Run your provisioning script inside the container.
4. Once the provisioning script is finished, tar up the result and save it to
   Velociraptor's file store.

After those steps are complete, you should be to go to Platform -> Apps, create
a new application or select an existing one, and link it to your stack.  When
you next build the app, the build will occur inside your newly built OS image.
When you deploy the app, the image will be downloaded and unpacked just like
the build is.

In time you may realize that you want to change something in the OS image.
Maybe you need to add a system-level package, or maybe there's an urgent
security fix.  You should modifyy your provisioning script to make the desired
change, edit your stack in the Velociraptor UI, upload your new script, and
click "Save and Build" as you did before.  When your image is done building, it
will be marked as the 'active' build in the stack, and will be used for all
builds and swarms of your app.

Base Images
===========

Velociraptor needs a base image as a starting point.  You can use a tarball
provided by an existing Linux distribution.  `Ubuntu's website`_ provides
minimal base images that you can use.

But!

There is `a bug`_ in stock Ubuntu 14.04 (Trusty) and CentOS 6.5 images that makes
them essentially unusable in containers, unless you disable PAM audit signals.
Some kind souls have implemented `that workaround`_ for Docker images, and it
works for Velociraptor as well.  You can download a Velociraptor-compatible
base image at http://cdn.yougov.com/build/ubuntu_trusty_pamfix.tar.gz.

Using vimage
============

Most Velociraptor functions have both a high level graphical user interface
and a lower level command line interface.  OS images are no exception.  The
vr.imager Python package is used by the Velociraptor server to build OS images,
and you can easily use it from the command line yourself.

These commands require that you run as root on a Linux host with LXC installed.

Install vr.imager::

    pip install vr.imager

Create a file named my_image.yaml with contents like this::

    base_image_url: http://cdn.yougov.com/build/ubuntu_trusty_pamfix.tar.gz
    base_image_name: ubuntu_trusty_pamfix 
    new_image_name: my_awesome_image_20141031
    script_url: /path/to/my_provisioning_script.sh
    env:
      PATH: /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

(As you may have guessed, any of the "_url" fields in that YAML file may be
given either an http url or a local file path.)

Tell vimage to build it::

    vimage build my_image.yaml

You should see all the steps in your provisioning script get executed in your
terminal.  When it's all done, you should have two new files in your current
directory::

    root@vagrant-ubuntu-trusty-64:~# ls -1
    my_awesome_image_20141031.log
    my_awesome_image_20141031.tar.gz
    my_image.yaml
    
If something goes wrong while running your provisioning script, you might want
to get into the container and debug interactively.  You can do so like this::

    vimage shell my_image.yaml

.. _Heroku's: https://devcenter.heroku.com/articles/stack
.. _`Ubuntu's website`: http://cdimage.ubuntu.com/ubuntu-core/trusty/daily/current/
.. _`a bug`: https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/patch/?id=543bc6a1a987672b79d6ebe8e2ab10471d8f1047
.. _`that workaround`: https://github.com/sequenceiq/docker-pam
