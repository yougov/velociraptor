#!/bin/bash

# For apps running in containers, this script will set up the container and
# then call the script to start the actual app.

# For uncontained apps, this script will do almost nothing, just calling the
# script with the actual command.
%(cmd)s 
