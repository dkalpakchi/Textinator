#!/bin/sh
(docker exec -i textinator_db_1 psql -U textinator || docker exec -i textinator-db-1 psql -U textinator) < $1
