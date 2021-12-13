# Textinator

## Installation
### Prerequisites
```
sudo apt-get install python3-pip npm gulp mysql-client-core-5.7
sudo npm install -g gulp-cli
npm install gulp -D
pip install -r requirements.txt --user
npm install
gulp build
```

If you want TinyMCE uploads to work, don't forget to run
```
python manage.py collectstatic
```

## Docker
Create and run container
1. Build and run container in the background mode: `docker-compose up -d --build`
2. Apply migrations: `docker-compose exec web python /usr/src/app/manage.py migrate --noinput`
3. Create superuser: `docker-compose exec web python /usr/src/app/manage.py createsuperuser`
4. Collect static data: `docker-compose exec web python /usr/src/app/manage.py collectstatic`
4. Go to `http://localhost:8000/textinator` in the browser of your choice

Take down container and DB:
`docker-compose down -v`