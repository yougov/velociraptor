web: gunicorn -c gunicorn_config.py 
worker: python project/manage.py celeryd -l info -c 4 -E
watcher: python project/manage.py celerycam 
beat: python project/manage.py celerybeat
