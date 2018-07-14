
import os
import sys
from celery import Celery
from django.apps import apps, AppConfig
from django.conf import settings


if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # pragma: no cover


from celery.signals import after_setup_logger
import logging
MyLogHandler = logging.StreamHandler(sys.stdout)

@after_setup_logger.connect()
def logger_setup_handler(logger, **kwargs ):
  my_handler = MyLogHandler
  my_handler.setLevel(logging.DEBUG) 
  my_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s') #custom formatter
  my_handler.setFormatter(my_formatter)
  logger.addHandler(my_handler)

  logging.info("My log handler connected -> Global Logging")



app = Celery('rink', broker="redis://")


class CeleryConfig(AppConfig):
    name = 'rink.taskapp'
    verbose_name = 'Celery Config'

    def ready(self):
        # Using a string here means the worker will not have to
        # pickle the object when using Windows.
        app.config_from_object('django.conf:settings')
        installed_apps = [app_config.name for app_config in apps.get_app_configs()]
        app.autodiscover_tasks(lambda: installed_apps, force=True)

        

        


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')  # pragma: no cover
