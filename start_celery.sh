#!/usr/bin/env bash

# First argument is the settings module to use.
if [ -n $1 ]; then
    export DJANGO_SETTINGS_MODULE=$1
fi

celery -A mavedb worker -l info