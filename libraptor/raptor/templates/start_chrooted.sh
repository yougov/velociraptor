#!/bin/bash

# This is a script to launch a Velociraptor proc after entering a chroot
# environment.  It's necessary because PATH, specifically, is not preserved
# when running 'chroot'.

# Ensure we have things like the java path in PATH
source /etc/profile

# stick the env at the beginning of the path.
export PATH=/release/env/bin:$PATH

# Tell the app where to find config and what port to use
export APP_SETTINGS_YAML="/release/settings.yaml"
export PORT=%(port)s

# Set a proc-specific temp dir
export TMPDIR="/tmp"

# start the app
cd /release
exec %(cmd)s 
