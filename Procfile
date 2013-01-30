web: gunicorn -c gunicorn_config.py vr.wsgi:app
worker: python project/manage.py celeryd -l info -c 4
beat: python project/manage.py celerybeat --pidfile=
