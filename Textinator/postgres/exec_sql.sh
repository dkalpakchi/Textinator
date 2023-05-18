#!/bin/bash
if [ "$1" = "dev" ]
then
  source .env.dev
else
  source .env.prod
fi
(docker exec -i textinator_db_1 psql -U $TT_DB_USER || docker exec -i textinator-db-1 psql -U $TT_DB_USER) < $2
