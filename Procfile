release: python src/manage.py migrate
web: gunicorn --pythonpath src django_project.wsgi:application --timeout 120 --forwarded-allow-ips="*"
worker: celery -A src.django_project worker -l info --concurrency=3
beat: celery -A src.django_project beat --loglevel=info
