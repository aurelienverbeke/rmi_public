#!/bin/bash

# Move into script folder
cd -- "$( dirname -- "$0" )"

docker compose -f compose.runner.yaml run -T --build runner psql < $1