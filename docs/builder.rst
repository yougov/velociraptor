Builder
=======

Velociraptor builds apps using Heroku buildpacks.  Builds are done in temporary
containers where the untrusted app and buildpack code can't do harm to the rest
of the system.

CLI
===

Velociraptor's build tool is called vr.builder, and can be installed like a
normal Python package::

  pip install vr.builder

That package provides a 'vbuild' command line tool that takes two arguments:

1. A subcommand of either 'build' or 'shell'.
2. The path to a yaml file that specifies the app, version, and buildpacks to
   be used to do the build.

Here's an example invocation of the vbuild command::

  vbuild build my_app.yaml

The vbuild tool must be run as root, as root permissions are (currently)
required to launch LXC containers.

The YAML file
=============

The yaml file given to vbuild should have the following keys

- app_name: Should be both filesystem-safe and have no dashes or spaces.
- app_repo_type: Should be either 'git' or 'hg'.
- app_repo_url: The location of the app's Git or Mercurial repository.
- version: The tag, branch, or revision hash to check out from the app
  repository.  *This must be a string.*  If your version number looks like a
  float (e.g. 9.0) then you must enclose it in quotes to make YAML treat it as
  a string.
- buildpack_urls: A list of URLs to the buildpacks that are allowed to build
  the app.  Each buildpack's 'detect' script will be run against the app in
  order to determine which buildpack to run.  If none matches, the vbuild
  command will exit with an error.  To specify a particular version of a
  buildpack, include the revision hash as the fragment portion of the URL.

Here's an example of a valid build yaml file::

  app_name: vr_python_example
  app_repo_type: hg
  app_repo_url: https://github.com/btubbs/vr_python_example 
  buildpack_urls:
  - https://github.com/heroku/heroku-buildpack-nodejs.git
  - https://github.com/heroku/heroku-buildpack-scala.git
  - https://github.com/yougov/yg-buildpack-python2.git
  version: v3

If you know which buildpack you want you can specify it directly with the
buildpack_url field::

  app_name: vr_python_example
  app_repo_type: hg
  app_repo_url: https://github.com/btubbs/vr_python_example 
  buildpack_url: https://github.com/yougov/yg-buildpack-python2.git
  version: v3

If you specify both a buildpack_url and a buildpack_urls list, the singular
buildpack_url setting will take precedence.

When you launch a build from Velociraptor's web interface, the build start
message will include the YAML used to do the build (click the wrench to see the
dialog with the YAML).  You can copy/paste this into a local YAML file and run
vbuild yourself to debug any problems with the build.

Output
======

When the build has completed there should be three new files in your current
working directory:

- build.tar.gz will contain the compiled result of the build.
- build_result.yaml will contain metadata about the build.  A build_result.yaml
  file can be fed back to vbuild to do the build over again with the same
  versions, buildpacks, etc.
- compile.log will contain all the output from running the buildpack's
  'compile' script on your app.  (In cases where none of the listed buildpacks
  can detect your app, compile.log will not be present.)

The Shell Command and Environment
=================================

In addition to the 'build' subcommand, the vbuild tool provides a 'shell'
subcommand.  You run it like this::

  vbuild shell my_app.yaml

The shell subcommand works with the same YAML format as the build subcommand.

If you find that a build is failing for some reason you can use 'vbuild
shell' to get a shell in the build environment and debug the problem.  You will
have exactly the same environment variables set, and the buildpacks and app
code will be checked out and mounted into your container exactly as they are at
build time.

You can also run the same script that Velociraptor runs inside the container to
execute the buildpack::

  /builder.sh /build /cache/buildpack_cache

Read the comments and source in builder.sh for more details.

Checkouts and Caches
====================

The vbuild tool keeps caches and copies of repositories on the local filesystem
in order to speed up compilation on subsequent builds.  All of these are kept
under /apps/builder.

- Applications are kept under /apps/builder/repo, and should be identifiable by
  the app_name provided in the YAML file.
- Buildpacks are kept under /apps/builder/buildpacks.
- The caches used by buildpacks are kept under /apps/builder/cache

In all cases, folder names will be appended with an MD5 hash of the app's or
buildpack's URL.  This avoids collisions when two apps or buildpacks use the
same name.

It is safe to delete the app repos, buildpacks, or caches saved by vbuild.  The
vbuild tool will re-download any repositories or re-create any directories it
needs.  Deletion of buildpack caches in particular is sometimes necessary if
a buildpack gets a cache into a weird state.
