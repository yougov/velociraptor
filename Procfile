web: gunicorn -c gunicorn_config.py vr.wsgi:app
worker: python vr/manage.py celeryd -l info -c 4
beat: python vr/manage.py celerybeat --pidfile=
