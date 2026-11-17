#!/bin/bash

set -a
source /viscalmon-lib/.env
set +a

mkdir -p $DIR_PPI
mkdir -p $DIR_AZI_DIST

nice -5 flask --app viscalmon.viewer.viewer run --host=0.0.0.0 --port $VIEWER_PORT
