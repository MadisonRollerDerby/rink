# PYTHONPATH=rink DJANGO_SETTINGS_MODULE=config.settings.local  celery -A rink.taskapp worker -l info  -E
PYTHONPATH='./rink' py.test --cov=rink
