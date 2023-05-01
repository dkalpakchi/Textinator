#!/bin/sh
cd Textinator
docker-compose exec web python /home/tt/Textinator/manage.py maintenance $1 || docker compose exec web python /home/tt/Textinator/manage.py maintenance $1
