#!/bin/bash

# Strict mode
set -euo pipefail
IFS=$'\n\t'

# psql -U postgres -h postgres -f /app/dbsetup.sql
python -m vr.server.manage syncdb --noinput
python -m vr.server.manage loaddata /app/bootstrap.json
