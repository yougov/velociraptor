web: env/bin/gunicorn --bind 0.0.0.0:$PORT --workers 2 --name velociraptor_web --log-level info wsgi:app
worker: env/bin/python project/manage.py celeryd -l info -c 4
watcher: env/bin/python project/manage.py celerycam 
