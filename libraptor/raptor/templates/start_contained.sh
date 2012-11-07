#!/bin/bash

# If you're viewing this inside a proc directory on an app host, this is the
# file used to actually start up a Velociraptor-managed process.

# If you're viewing this inside our source code repo, this file is a template
# that will be used to write a real start script at deploy time.  The magic
# strings will be substituted with real values at that time.

source /etc/profile
export APP_SETTINGS_YAML="/app/settings.yaml"
export PORT=%(port)s
export TMPDIR=/tmp

CMD="%(cmd)s"
PROCNAME=%(procname)s
PROCS_ROOT=%(procs_root)s
lxc-execute --name $PROCNAME -f $PROCS_ROOT/$PROCNAME/proc.lxc -- su --preserve-environment -c "PATH=/app/env/bin:$PATH cd /app;$CMD" %(user)s
