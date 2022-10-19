![Textinator logo](https://github.com/dkalpakchi/Textinator/raw/master/docs/source/logo.png "Textinator")

[![DOI](https://zenodo.org/badge/192495914.svg)](https://zenodo.org/badge/latestdoi/192495914)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/1ac2ba5f4bc14883a02cd395df913859)](https://www.codacy.com/gh/dkalpakchi/Textinator/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=dkalpakchi/Textinator&amp;utm_campaign=Badge_Grade)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

## New here?

Check out some introductory resources:

*   [Documentation](https://textinator.readthedocs.io/en/latest/)
*   [Video tutorials](https://www.youtube.com/channel/UCUVbyJJFIUwfl129FGhPGJw)

## Try out Textinator on your own machine

First you will need to [install Docker](https://docs.docker.com/engine/install/) and [docker-compose](https://docs.docker.com/compose/install/). Afterwards just follow these steps:

1.  Clone this repository by running `git clone https://github.com/dkalpakchi/Textinator.git` or download one of the releases and unpack it.
2.  Build and run container in either development or production mode, following the instructions below

## Running in production mode

The recommended solution is to use nginx-gunicorn-docker setup, which we provide for out of the box if you run the following command. **NOTE** Before running the command, please replace the values within the angle brackets (<>) in the `.env.prod` file! Make sure none of those values are published anywhere, since they will compromise the security of your Textinator instance!

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up`

Now if you go to `http://localhost:1337`, you should see Textinator's main page.

Note that this command will build the Docker image only once and thus will copy the code only once. If you've some changes to the code and want to include them, you'll need to add a `--build` flag at the end of the command above.

To stop container, run:

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml stop`

To run container again, run:

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d`

To stop container AND take down the DB, run:

`docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml down -v`

### Exposing the ports and HTTPS

By default Textinator's port is `1337` and it is exposed only to the localhost and all requests are handled as HTTP to not impose any particular SSL certificate for handling HTTPS requests. To handle HTTPS, you'll need to set it up on your own server and then just reverse proxy to `http://localhost:1337`.

### Serve on a custom (sub)domain

It's absolutely possible to use custom domain, but first you need to let Textinator know that your domain is allowed. You can do this by adding your domain(s) to the `DJANGO_ALLOWED_HOSTS` variable in the `.env.prod` file (note that the list of domains is space-separated).

### Serve on a custom URL

If you have a server with a domain that hosts multiple applications, but you're unable to order subdomains for it, you might want to consider hosting Textinator on a specific URL. This is possible and requires the following steps (for this example we'll assume your custom URL is `mydomain.com/textinator` and we assume that you've already let Textinator know that `mydomain.com` is allowed).

1.  Change `ROOT_URLPATH` to `textinator/` (note that the trailing `/` is **mandatory**) in the `.env.prod` file.
2.  Change `location /static/` to `location /textinator/static/` and `location /media/` to `location /textinator/media/` in the `nginx/nginx.conf` file.
3.  Re-route all other URLs:
    *   If you host Textinator as a part of another server, then let `/textinator` point to `http://localhost:1337`
    *   If you host a standalone instance of Textinator, change `location /` to `location /textinator/` in the `nginx/nginx.conf`

### Database backup

We recommend to schedule a cron job to make a backup of the database. For example, making a backup every day at 16:00 would translate into the following cron task (assuming you want to save your dumps into `/home/your_user/textinator_dumps` folder of your server):

`0 16 * * * docker exec -i textinator_db_1 pg_dump -U textinator > /home/your_user/textinator_dumps/$(date +\%s).sql`

**NOTE** Escaping (putting `\` before) `%s` is mandatory, since cron interprets `%` as a newline character otherwise.

## Running in development mode

The development version will run the Django's built-in development server and will also map your local folder to that inside the Docker container, so that the changes in the code are immediately reflected without the need to restart the container. You can start Textinator in the dev mode using the following command.

`docker-compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up`

Now if you go to `http://localhost:8000`, you should see Textinator's main page.

The commands to stop the container and take down the DB are the same as in production mode, but you need to replace `prod` with `dev` everywhere.

## Internationalization

The software is developed in English.

Full translation is available for these languages (in alphabetical order):

*   \[x] Russian thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)
*   \[x] Swedish thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)
*   \[x] Ukrainian thanks to [Dmytro Kalpakchi](https://github.com/dkalpakchi)

Upcoming languages

*   \[ ] Dutch
*   \[ ] Spanish

## Contributing

Want to contribute to Textinator? Check out our [Contribution guidelines](https://github.com/dkalpakchi/Textinator/blob/master/CONTRIBUTING.md).

## Developer guide

A good starting place for familiarizing yourself with a codebase is via our [API documentation](https://textinator.readthedocs.io/en/latest/api.html). The documentation for developers is an ongoing effort, but some established workflows are described in our [Development guidelines](https://github.com/dkalpakchi/Textinator/blob/master/DEVELOPING.md).

## Credits

This project, as it is now, would be impossible without numerous other open-source projects (in alphabetical order, hopefully):

*   [Babel](http://babel.pocoo.org/en/latest/)
*   [Django](https://www.djangoproject.com/)
*   [django\_admin\_json\_editor](https://github.com/abogushov/django-admin-json-editor)
*   [django\_admin\_rangefilter](https://github.com/silentsokolov/django-admin-rangefilter)
*   [django-chartjs](https://github.com/peopledoc/django-chartjs)
*   [django-colorfield](https://github.com/fabiocaccamo/django-colorfield)
*   [django\_filebrowser\_no\_grappelli](https://github.com/smacker/django-filebrowser-no-grappelli)
*   [django-guardian](https://github.com/django-guardian/django-guardian)
*   [django-jazzmin](https://github.com/farridav/django-jazzmin)
*   [django-modeltranslation](https://github.com/deschler/django-modeltranslation)
*   [django-nested-admin](https://github.com/theatlantic/django-nested-admin)
*   [django-registration](https://github.com/ubernostrum/django-registration/)
*   [django-rosetta](https://pypi.org/project/django-rosetta/)
*   [django-sass-processor](https://github.com/jrief/django-sass-processor)
*   [django-scientific-survey](https://github.com/dkalpakchi/django-scientific-survey)
*   [django-tinymce4-lite](https://github.com/romanvm/django-tinymce4-lite)
*   [Jinja2](https://jinja2docs.readthedocs.io/en/stable/)
*   [PostgreSQL](https://www.postgresql.org/)
*   reportlab
