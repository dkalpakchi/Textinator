#!/bin/sh
cd Textinator
docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up --build || docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up --build
