#!/bin/sh
docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up --build
