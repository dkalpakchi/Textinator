#!/bin/sh
docker-compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up $1
