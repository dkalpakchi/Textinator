![Textinator logo](https://github.com/dkalpakchi/Textinator/raw/master/docs/source/logo.png "Textinator")

## New here?
Check out some introductory resources:
- [Documentation](https://textinator.readthedocs.io/en/latest/)
- [Video tutorials](https://www.youtube.com/channel/UCUVbyJJFIUwfl129FGhPGJw)

## Try out Textinator on your own machine
First you will need to [install Docker](https://docs.docker.com/engine/install/) and [docker-compose](https://docs.docker.com/compose/install/). Afterwards just follow these steps:
1. Build and run container in the background mode: `docker-compose up -d --build`
2. Go to `http://localhost:8000/` in the browser of your choice

To stop container, run:
`docker-compose stop`

To run container again, run:
`docker-compose up -d`

To stop container AND take down the DB, run:
`docker-compose down -v`

## Running Textinator in production
We recommend using nginx-gunicorn-docker setup. A more extensive tutorial is on its way.

## Internationalization

The software is developed in English.

Full translation is available for these languages (in alphabetical order):

* [x] Russian thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)
* [x] Ukrainian thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)

Partial translation is available for these languages (in alphabetical order):
* [ ] Swedish (61%) thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)

Upcoming languages
* [ ] Dutch
* [ ] Spanish

## Contributing
Want to contribute to Textinator? Check out our [Contribution guidelines](https://github.com/dkalpakchi/Textinator/blob/master/CONTRIBUTING.md).

## Developer guide

A good starting place for familiarizing yourself with a codebase is via our [API documentation](https://textinator.readthedocs.io/en/latest/api.html). The documentation for developers is an ongoing effort, but some established workflows are described in our [Development guidelines](https://github.com/dkalpakchi/Textinator/blob/master/DEVELOPING.md).

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
