web: gunicorn -c gunicorn_config.py vr.server.wsgi:app
worker: vr_worker
beat: vr_beat
migrate: bash run_migrations.sh
