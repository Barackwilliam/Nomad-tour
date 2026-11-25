#!/usr/bin/env bash
# Render build step (Build Command = ./build.sh)
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_admin
# Loads the starting tours, departures and photos the first time only.
python manage.py seed_site --if-empty
