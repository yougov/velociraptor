web: env/bin/gunicorn --bind 0.0.0.0:$PORT --workers 4 --name velociraptor_web --log-level info wsgi:app
worker: env/bin/python project/manage.py celeryd -l info -c 4 -E
watcher: env/bin/python project/manage.py celerycam 
beat: env/bin/python project/manage.py celerybeat
