#!/bin/bash
# By using an inner wrapper script like this we can support using app-specific
# env vars like $DBURL on the Procfile's command line.  Fixes #26 

# Load up environment variables in order of least specific to most specific.
export TMPDIR=%(tmp)s
export HOME=%(home)s

# scripts in .profile.d may come from the app or from the buildpack.
if (test -d $HOME/.profile.d); then
	for f in `ls $HOME/.profile.d`; do
		source $HOME/.profile.d/$f
	done
fi

# These env vars are from release-specific config.
source %(envsh)s
export APP_SETTINGS_YAML="%(settings)s"

# We control the port.  Don't allow env.sh or .profile.d to override it.
export PORT=%(port)s

# Launch the actual program with 'exec', making the process replace this one
# (rather than being a child).  The app's command is special cased with this
# 'run' option so it can be written into the script instead of having to be
# passed as an argument, which can be tricky when it's got its own long
# argument list and variable expansion going on.
if [ "run" == "$1" ]
then
  exec %(cmd)s
else
  exec $@
fi
