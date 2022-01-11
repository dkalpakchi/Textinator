python /usr/src/Textinator/manage.py migrate --noinput
python /usr/src/Textinator/manage.py collectstatic --noinput
python /usr/src/Textinator/manage.py seed_default
python /usr/src/Textinator/manage.py update_translation_fields projects
python /usr/src/Textinator/manage.py createsuperuser --noinput
python /usr/src/Textinator/manage.py runserver 0.0.0.0:8000