#!/bin/bash

# Move into script folder
cd -- "$( dirname -- "$0" )"

# To get LOGS_DIR
set -a
source .env
set +a

# Docker will write in it
mkdir -p $LOGS_DIR
chgrp $LOGS_GROUP_NAME $LOGS_DIR
chmod 2775 $LOGS_DIR

docker compose -f compose.runner.yaml run --interactive --rm --build runner "$@"