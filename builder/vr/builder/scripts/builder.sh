#!/bin/bash

# This script builds apps using buildpacks.

# It accepts two command line arguments:
# 1. The location of the application to be built.
# 2. The location of the folder where build assets may be cached.

# Additionally, ONE of either the BUILDPACK_DIRS or BUILDPACK_DIR environment
# variables must be set.

# BUILDPACK_DIR, if provided, should be the path to the buildpack to be used to
# build this app.

# If BUILDPACK_DIR is not provided, then BUILDPACK_DIRS will be used to set it.
# BUILDPACK_DIRS should be a list of buildpack directories, joined with the
# colon (":") character (just like PATH).  The buildpack to use when building
# the app will be selected by running each buildpack's "detect" script on the
# app until one of the buildpacks succeeds at detecting the app.  If no
# buildpack detects the app, the script will exit immediately.

# Once the buildpack has been determined, the script will call the buildpack's
# "compile" script, passing in the application and cache dirs.

# After compilation has finished, the script will run the buildpack's "release"
# script and write the output to <app dir>/.release.yaml


APP_DIR=$1
CACHE_DIR=$2

# APP_DIR and CACHE_DIR must be provided.
SYNTAX="Syntax: $0 <app dir> <cache dir>"
: ${APP_DIR:?$SYNTAX}
: ${CACHE_DIR:?$SYNTAX}

# APP_DIR and CACHE_DIR must be directories.

if [ ! -d "$APP_DIR" ]; then
  echo "Error: First argument (app dir) must be a directory."
  exit 1
fi

if [ ! -d "$CACHE_DIR" ]; then
  echo "Error: Second argument (cache dir) must be a directory."
  exit 1
fi

if [ -z "$BUILDPACK_DIR" ]; then
  echo "BUILDPACK_DIR not set.  Detecting..."
  if [ -z "$BUILDPACK_DIRS" ]; then
    echo "BUILDPACK_DIRS also not set.  Aborting!"
    exit 1
  fi

  IFS=':' read -ra BUILDPACKS <<< "$BUILDPACK_DIRS"
  for i in "${BUILDPACKS[@]}"; do
      $i/bin/detect $APP_DIR
      returncode=$?
      if [[ $returncode == 0 ]]; then
        BUILDPACK_DIR=$i
        break
      fi
  done
  if [ -z "$BUILDPACK_DIR" ]; then
    echo "Error: No compatible buildpack in $BUILDPACK_DIRS."
    exit 1
  fi
fi

echo "Compiling app with $BUILDPACK_DIR"
set -eo pipefail
$BUILDPACK_DIR/bin/compile $APP_DIR $CACHE_DIR

# Record the output of the release script.
$BUILDPACK_DIR/bin/release $APP_DIR > $APP_DIR/.release.yaml

# Record which buildpack was used.
echo "$BUILDPACK_DIR" > $APP_DIR/.buildpack
