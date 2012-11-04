#!/bin/bash

# If you're viewing this inside a proc directory on an app host, this is the
# file used to actually start up a Velociraptor-managed process.

# If you're viewing this inside our source code repo, this file is a template
# that will be used to write a real start_proc.sh at deploy time.  The magic
# strings will be substituted with real values by Python.

# Ensure we have things like the java path in PATH
source /etc/profile

# stick the env at the beginning of the path.
export PATH=%(env_bin_path)s:$PATH

# Tell the app where to find config and what port to use
export APP_SETTINGS_YAML="%(settings_path)s"
export PORT=%(port)s

# Set a proc-specific temp dir
export TMPDIR=%(tmpdir)s

# start the app
exec %(cmd)s 
