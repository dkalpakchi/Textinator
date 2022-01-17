![Textinator logo](https://github.com/dkalpakchi/Textinator/raw/master/docs/source/logo.png "Textinator")

## Features upcoming in v1.1 (tentative)
- _Editor role_. Now editing is only possible via the admin interface by the system administrator. That is to ensure the quality of edits. In the next version, we present an "Editor" role allowing the promoted annotators to edit annotations themselves via regular UI.
- _Undo last_. By design annotators are not allowed to delete their edits, since these "misedits" might end up being useful for researchers. However, they will be able to undo their last annotation in the next version (this is almost done now, just needs more testing).
- _Suggestions API_.
- _Reviewer role_.


## Installation
Create and run container
1. Build and run container in the background mode: `docker-compose up -d --build`
2. Go to `http://localhost:8000/textinator` in the browser of your choice

Take down container and DB:
`docker-compose down -v`


## Contributing
Want to contribute to Textinator? Awesome, we are very grateful for that! There are multiple ways to contribute:

1. Find and report bugs
2. Suggest an enhancement
3. Write automated tests
4. Help translating Textinator into new languages


## Developer guide

### Working with static translations
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