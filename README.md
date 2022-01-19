![Textinator logo](https://github.com/dkalpakchi/Textinator/raw/master/docs/source/logo.png "Textinator")

## New here?
Check out some introductory resources:
- [Documentation](https://textinator.readthedocs.io/en/latest/)
- [Video tutorials](https://www.youtube.com/channel/UCUVbyJJFIUwfl129FGhPGJw)

## Try out Textinator on your own machine
First you will need to [install Docker](https://docs.docker.com/engine/install/) and [docker-compose](https://docs.docker.com/compose/install/). Afterwards just follow these steps:
1. Build and run container in the background mode: `docker-compose up -d --build`
2. Go to `http://localhost:8000/textinator` in the browser of your choice

To stop container, run:
`docker-compose stop`

To run container again, run:
`docker-compose up -d`

To stop container AND take down the DB, run:
`docker-compose down -v`

## Running Textinator in production
We recommend using nginx-gunicorn-docker setup. A more extensive tutorial is on its way.

## Contributing
Want to contribute to Textinator? Awesome, we are very grateful for that! There are multiple ways to contribute.

### Find and report bugs
We are very grateful for every bug that you manage to spot! Please open a new GitHub issue and use [a template for a bug report](https://github.com/dkalpakchi/Textinator/issues/new?assignees=&labels=&template=bug_report.md&title=)

### Suggest an enhancement
If you have an idea on how to make Textinator better, please suggest it via opening [a feature request](https://github.com/dkalpakchi/Textinator/issues/new?assignees=&labels=&template=feature_request.md&title=). Let's discuss it and maybe your feature will make it to the next release of Textinator!

### Help translating Textinator into new languages
If you want to help localize Textinator to a new language, please open [a translation request](https://github.com/dkalpakchi/Textinator/issues/new?assignees=&labels=&template=translation-request.md&title=) and we'll take it from there.

### Write automated tests
Currently Textinator is mostly tested manually, so we would be very grateful for any kinds of tests: unit tests, integration tests or interaction tests. Please open a GitHub issue, assign it a *testing* label and describe what kind of tests you are willing to do.

## Developer guide

A good starting place for familiarizing yourself with a codebase is via our [API documentation](https://textinator.readthedocs.io/en/latest/api.html). The documentation for developers is an ongoing effort, but some established workflows are described below.

### Working with static translations
We use Babel:
- https://babel.pocoo.org/en/latest/messages.html#message-extraction
- https://babel.pocoo.org/en/latest/cmdline.html#cmdline

A general workflow consists of these steps:

Step 1: generate a POT file:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel extract -F babel.cfg -o locale/translations.pot ."`

Step 2: generate a specific translation file from a POT file:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel init -d locale -l <locale-code> -i locale/translations.pot -D django"`

Step 3: update translations for any language run:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel update -d locale -l <locale-code> -i locale/translations.pot -D django"`

Step 4: compile the updated translations:
`docker-compose exec web sh -c "cd /usr/src/Textinator && PATH=$PATH:/home/textinator/.local/bin pybabel compile -d locale -l <locale-code> -D django"`

First run steps 1 to 4. Next if you need to update your translations, **skip step 2** for languages with **already existing translations**.

### Working with dynamic translations
We're using django-model-translation for this purpose and the workflow is as follows:
1. Add your model and desirable fields for translation in `projects/translation.py` and register it in the same file.
2. Make & apply migrations by running
```
docker-compose exec web python /usr/src/Textinator/manage.py makemigrations projects
docker-compose exec web python /usr/src/Textinator/manage.py migrate projects --noinput
```
3. Update default values by running
```
docker-compose exec web python /usr/src/Textinator/manage.py update_translation_fields projects
```

### Useful commands
Here is the list of useful commands that has not found their own documentation section yet.

To load the DB dump into the Docker container:
`cat <your-dump-file>.sql | docker exec -i textinator_db_1 psql -U textinator`


## Credits
This project, as it is now, would be impossible without numerous other open-source projects (in alphabetical order, hopefully):
- [Babel](http://babel.pocoo.org/en/latest/)
- [Django](https://www.djangoproject.com/)
- [django_admin_json_editor](https://github.com/abogushov/django-admin-json-editor)
- [django_admin_rangefilter](https://github.com/silentsokolov/django-admin-rangefilter)
- [django-chartjs](https://github.com/peopledoc/django-chartjs)
- [django-colorfield](https://github.com/fabiocaccamo/django-colorfield)
- [django_filebrowser_no_grappelli](https://github.com/smacker/django-filebrowser-no-grappelli)
- [django-guardian](https://github.com/django-guardian/django-guardian)
- [django-jazzmin](https://github.com/farridav/django-jazzmin)
- [django-modeltranslation](https://github.com/deschler/django-modeltranslation)
- [django-nested-admin](https://github.com/theatlantic/django-nested-admin)
- [django-registration](https://github.com/ubernostrum/django-registration/)
- [django-rosetta](https://pypi.org/project/django-rosetta/)
- [django-sass-processor](https://github.com/jrief/django-sass-processor)
- [django-scientific-survey](https://github.com/dkalpakchi/django-scientific-survey)
- [django-tinymce4-lite](https://github.com/romanvm/django-tinymce4-lite)
- [Jinja2](https://jinja2docs.readthedocs.io/en/stable/)
- [PostgreSQL](https://www.postgresql.org/)
- reportlab
