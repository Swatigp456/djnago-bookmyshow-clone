#!/bin/bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
DATABASE_URL=$POSTGRES_URL_NON_POOLING python manage.py migrate
