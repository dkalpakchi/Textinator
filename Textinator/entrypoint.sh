#!/bin/sh
export PATH="$PATH:/home/tt/.local/bin"

PREFIX=/home/tt/Textinator

cd $PREFIX

/usr/bin/supervisord -c $PREFIX/memcached.conf

if [ "$TT_ENV" = "dev" ]; then
	npm install --prefix $PREFIX
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py update_translation_fields projects
python manage.py seed_default
python manage.py update_marker_actions
python manage.py createsuperuser --noinput

REDIS_URLS="textinator_redis_1 textinator-redis-1"

for url in $REDIS_URLS
do
  if ping -c 5 $url &> /dev/null
  then
    echo "[Redis] Success for $url -- chosen!"
    export REDIS_URL=$url
    break
  else
    echo "[Redis] Couldn't ping $url -- ignoring"
  fi
done

if [ "$TT_ENV" = "dev" ]; then
  tmux new-session -d -s textinator_celery
  tmux send-keys -t textinator_celery "cd /home/tt/Textinator" Enter
  tmux send-keys -t textinator_celery "python manage.py start_celery_worker" Enter
  python manage.py runserver 0.0.0.0:8000
else
  celery -A Textinator multi start worker --pidfile="$HOME/run/celery/Textinator/%n.pid" --logfile="$HOME/log/celery/Textinator/%n%I.log"
	mkdir -p -- $PREFIX/log/gunicorn
	gunicorn --access-logfile log/gunicorn/access_log --error-logfile log/gunicorn/error_log -b 0.0.0.0:8000 Textinator.wsgi --timeout 500
fi
