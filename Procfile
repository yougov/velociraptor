web: env/bin/gunicorn -c gunicorn_config.py wsgi:app
worker: env/bin/python project/manage.py celeryd -l info -c 4 -E
watcher: env/bin/python project/manage.py celerycam 
beat: env/bin/python project/manage.py celerybeat
