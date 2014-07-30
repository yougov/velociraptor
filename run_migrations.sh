#!/bin/bash

python server/vr/server/manage.py migrate $MIGRATE_ARGS

# Sleeping...
if [[ $SLEEP_FOREVER == "true" ]]
then
    cat
fi

echo 'Done!'
