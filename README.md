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
2. Apply migrations: `docker-compose exec web python /usr/src/Textinator/manage.py migrate --noinput`
3. Create superuser: `docker-compose exec web python /usr/src/Textinator/manage.py createsuperuser`
4. Collect static data: `docker-compose exec web python /usr/src/Textinator/manage.py collectstatic`
5. Go to `http://localhost:8000/textinator` in the browser of your choice

Take down container and DB:
`docker-compose down -v`

To load the DB dump into the docker container:
`cat <your-dump-file>.sql | docker exec -i textinator_db_1 psql -U textinator`


## Translations to multiple languages
We use Babel:
- https://babel.pocoo.org/en/latest/messages.html#message-extraction
- https://babel.pocoo.org/en/latest/cmdline.html#cmdline

Step 1: generate a POT file:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel extract -F babel.cfg -o locale/translations.pot ."`

Step 2: generate a specific translation file from a POT file:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel init -d locale -l <locale-code> -i locale/translations.pot -D django"`

Step 3: update translations for any language run:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel update -d locale -l <locale-code> -i locale/translations.pot -D django"`

Step 4: compile the updated translations:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel compile -d locale -l <locale-code> -D django"`

First run steps 1 to 4. Next if you need to update your translations, **skip step 2** for languages with **already existing translations**.