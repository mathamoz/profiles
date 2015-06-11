web: gunicorn app:app --log-file=-
worker: celery worker -A app.celery --loglevel=info
