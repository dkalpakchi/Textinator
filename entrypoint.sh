export PATH="$PATH:/home/tt/.local/bin"

PREFIX=/home/tt/Textinator

if [ "$TT_ENV" = "dev" ]; then
	npm install --prefix $PREFIX
fi
python $PREFIX/manage.py migrate --noinput
python $PREFIX/manage.py collectstatic --noinput
python $PREFIX/manage.py seed_default
python $PREFIX/manage.py update_translation_fields projects
python $PREFIX/manage.py update_marker_actions
python $PREFIX/manage.py createsuperuser --noinput

if [ "$TT_ENV" = "dev" ]; then
	python $PREFIX/manage.py runserver 0.0.0.0:8000
else
	mkdir -p -- $PREFIX/log/gunicorn
	cd $PREFIX
	gunicorn --access-logfile log/gunicorn/access_log --error-logfile log/gunicorn/error_log -b 0.0.0.0:8000 Textinator.wsgi
fi