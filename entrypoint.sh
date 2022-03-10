npm install --prefix /home/tt/Textinator
python /home/tt/Textinator/manage.py migrate --noinput
python /home/tt/Textinator/manage.py collectstatic --noinput
python /home/tt/Textinator/manage.py seed_default
python /home/tt/Textinator/manage.py update_translation_fields projects
python /home/tt/Textinator/manage.py update_marker_actions
python /home/tt/Textinator/manage.py createsuperuser --noinput
python /home/tt/Textinator/manage.py runserver 0.0.0.0:8000