#!/bin/sh
set -eu

echo "[entrypoint] Django settings: ${DJANGO_SETTINGS_MODULE:-pushdemo.settings.local}"

python manage.py migrate --noinput
python manage.py ensure_vapid_keys
python manage.py ensure_demo_user

if [ "${RUN_MODE:-local}" = "test" ]; then
  python manage.py collectstatic --noinput
  exec gunicorn pushdemo.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-2}" --timeout 60
fi

exec python manage.py runserver 0.0.0.0:8000
