#!/bin/bash

# Move into script folder
cd -- "$( dirname -- "$0" )"

docker compose -f compose.runner.yaml build runner
docker compose -f compose.runner.yaml run -T runner pg_dump > dump_`date +%Y-%m-%d"_"%H_%M_%S`.sql