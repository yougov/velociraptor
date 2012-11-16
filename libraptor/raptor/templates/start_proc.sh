#!/bin/bash

# If you're viewing this inside a proc directory on an app host, this is the
# file used to actually start up a Velociraptor-managed process.

# If you're viewing this inside our source code repo, this file is a template
# that will be used to write a real start_proc.sh at deploy time.  The magic
# strings will be substituted with real values by Python.

export APP_SETTINGS_YAML="%(settings_path)s"
export PORT=%(port)s
export TMPDIR=%(tmpdir)s

source %(envsh_path)s
exec %(cmd)s 
