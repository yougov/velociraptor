web: env/bin/gunicorn --bind 0.0.0.0:$PORT --workers 2 --name velociraptor_web --log-level info wsgi:app
worker: env/bin/python manage.py celeryd -l info -c 4
