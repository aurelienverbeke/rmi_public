#!/bin/bash

# Move into script folder
cd -- "$( dirname -- "$0" )"

set -a
source viscalmon-lib/.env
set +a

docker compose -f compose.viewer.yaml down -v