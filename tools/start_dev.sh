#!/bin/sh
cd Textinator
docker-compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up --build
