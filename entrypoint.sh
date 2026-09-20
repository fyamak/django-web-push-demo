#!/bin/sh
set -eu

MODE="${1:-local}"

if [ "$MODE" = "test" ]; then
  export DJANGO_SETTINGS_MODULE="pushdemo.settings.test"
else
  export DJANGO_SETTINGS_MODULE="pushdemo.settings.local"
fi

echo "[entrypoint] Mode: $MODE"
echo "[entrypoint] Django settings: $DJANGO_SETTINGS_MODULE"

python manage.py migrate --noinput
python manage.py ensure_vapid_keys
python manage.py ensure_demo_user

if [ "$MODE" = "test" ]; then
  python manage.py collectstatic --noinput
  # network_mode: host kullanildigi icin Gunicorn dogrudan host localhost:5001'e
  # bind edilir. Host Nginx ayni adrese proxy yapar.
  exec gunicorn pushdemo.wsgi:application --bind 127.0.0.1:5001 --workers 2 --timeout 60
fi

exec python manage.py runserver 0.0.0.0:8000
