web: gunicorn -c gunicorn_config.py vr.wsgi:app
worker: python vr_django/vr/manage.py celeryd -l info -c 4
beat: python vr_django/vr/manage.py celerybeat --pidfile=
