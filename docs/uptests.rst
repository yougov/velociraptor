Uptests
=======

Uptests are an essential part of Velociraptor's promise of zero-downtime
deployment.  The idea is that a deployment should look like this:

1. You have some instances of your app already deployed, but you want to update
   the code or config.
2. You deploy new instances with the new code or config, while leaving the old
   instances up and still handling traffic.  The new instances don't handle any
   traffic yet.
3. You run tests on the new instances to ensure that they're running happily
   and ready to serve traffic.
4. If the tests pass, then you change your routing rules to serve traffic from
   the new instances instead of the old ones.
5. Finally, you take down the old instances.

Velociraptor automates all of the above steps when you swarm.  All you have to
do as a developer is include some uptests.

Definition
==========

An uptest is a small script or program that checks whether a single instance
of an app is running correctly.

Running
=======

Uptests scripts must be executable files.  They accept two command line
arguments: "host" and "port".  Uptests are run in an environment identical to
production (same build, same environment variables), but not necessarily on
the same host as the proc being tested.  The uptest should exercise the
designated proc in some way to check whether it's ready to accept production
traffic.  

Results
=======

If successful, the uptest script must exit with status code 0.  Any other
exit code signifies a failure.  The script may emit debug information to
stdout or stderr.

Organization
============

Each proc in an app has different uptests, organized by subfolders of an
'uptests' folder in the project root.  In the example below, the web proc has
3 uptests, which will be executed in the order listed by the OS.

::
  |
  +-- Procfile
  |
  +-- README.rst
  |
  +-- uptests/
     |
     +-- web/
        |
        +-- 01_its_alive.py
	|
        +-- 02_login_required.py
	|
        +-- 03_check_rss.py
