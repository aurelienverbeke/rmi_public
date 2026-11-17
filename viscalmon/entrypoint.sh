#!/bin/bash

umask 002

set -a
source /viscalmon-lib/.env
set +a

if [ "$#" -eq 0 ]; then
    exec bash
else
    exec "$@"
fi