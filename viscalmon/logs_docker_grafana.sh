#!/bin/bash

# Move into script folder
cd -- "$( dirname -- "$0" )"

docker compose -f compose.daemons.yaml grafana