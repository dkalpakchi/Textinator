# Developer guidelines

## Running in development mode

The development version will run the Django's built-in development server and will also map your local folder to that inside the Docker container, so that the changes in the code are immediately reflected without the need to restart the container. You can start Textinator in the dev mode by running `sh tools/start_dev.sh` after cloning the repo. This will effectively do the following:
```
cd Textinator
docker-compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml up
```

Now if you go to `http://localhost:8000`, you should see Textinator's main page.

The commands to stop the container and take down the DB are the same as in production mode, but you need to replace `prod` with `dev` everywhere.

## Working with static translations

We use Babel:

*   https://babel.pocoo.org/en/latest/messages.html#message-extraction
*   https://babel.pocoo.org/en/latest/cmdline.html#cmdline

A general workflow consists of these steps:

Step 1: generate a POT file:
`docker-compose exec web sh -c "cd /home/tt/Textinator && PATH=$PATH:/home/tt/.local/bin pybabel extract -F babel.cfg -o locale/translations.pot ."`

Step 2: generate a specific translation file from a POT file:
`docker-compose exec web sh -c "cd /home/tt/Textinator && PATH=$PATH:/home/tt/.local/bin pybabel init -d locale -l <locale-code> -i locale/translations.pot -D django"`

Step 3: update translations for any language run:
`docker-compose exec web sh -c "cd /home/tt/Textinator && PATH=$PATH:/home/tt/.local/bin pybabel update -d locale -l <locale-code> -i locale/translations.pot -D django"`

Step 4: compile the updated translations:
`docker-compose exec web sh -c "cd /home/tt/Textinator && PATH=$PATH:/home/tt/.local/bin pybabel compile -d locale -l <locale-code> -D django"`

First run steps 1 to 4. Next if you need to update your translations, **skip step 2** for languages with **already existing translations**.

## Working with dynamic translations

We're using django-model-translation for this purpose and the workflow is as follows:

1.  Add your model and desirable fields for translation in `projects/translation.py` and register it in the same file.
2.  Make & apply migrations by running (**from the root folder with Textinator code**)

```bash
docker-compose exec web python /home/tt/Textinator/manage.py makemigrations projects
docker-compose exec web python /home/tt/Textinator/manage.py migrate projects --noinput
```

3.  Update default values by running

```bash
docker-compose exec web python /home/tt/Textinator/manage.py update_translation_fields projects
```

## Useful commands

Here is the list of useful commands that has not found their own documentation section yet.

To load the DB dump into the Docker container:
`cat <your-dump-file>.sql | docker exec -i textinator_db_1 psql -U textinator`
