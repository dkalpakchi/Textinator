export PATH="$PATH:/home/tt/.local/bin"

PREFIX=/home/tt/Textinator

cd $PREFIX

if [ "$TT_ENV" = "dev" ]; then
	npm install --prefix $PREFIX
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_default
python manage.py update_translation_fields projects
python manage.py update_marker_actions
python manage.py createsuperuser --noinput

if [ "$TT_ENV" = "dev" ]; then
	python manage.py runserver 0.0.0.0:8000
else
	mkdir -p -- $PREFIX/log/gunicorn
	gunicorn --access-logfile log/gunicorn/access_log --error-logfile log/gunicorn/error_log -b 0.0.0.0:8000 Textinator.wsgi --timeout 500
fi