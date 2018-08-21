
import os
from celery import Celery
from django.apps import apps, AppConfig
from django.conf import settings

if not settings.configured:
    # set the default Django settings module for the 'celery' program.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # pragma: no cover

app = Celery(
    'rink',

    task_always_eager=False,
    task_time_limit=10,
    redis_socket_connect_timeout=10,
    redis_socket_timeout=8,
    broker_connection_timeout=9,
    #broker="amqp://guest:guest@localhost:5672/test_rink",
    #backend="amqp://guest:guest@localhost:5672/test_rink",

    broker="redis://",
    broker_transport="redis",
    broker_url='redis://localhost:6379',
    result_backend='redis',  #://localhost:6379',

    #accept_content=['json'],
    #task_serializer='json',
    #result_serializer='json',
)


class CeleryConfig(AppConfig):
    name = 'rink.taskapp'
    verbose_name = 'Celery Config'

    def ready(self):
        # Using a string here means the worker will not have to
        # pickle the object when using Windows.
        #app.config_from_object('django.conf:settings', namespace='CELERY')
        installed_apps = [app_config.name for app_config in apps.get_app_configs()]
        app.autodiscover_tasks(lambda: installed_apps, force=True)
        
app.conf.task_always_eager = True


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')  # pragma: no cover


#. https://stackoverflow.com/questions/46530784/make-django-test-case-database-visible-to-celery/46564964#46564964
@app.task(name='celery.ping')
def ping():
    # type: () -> str
    """Simple task that just returns 'pong'."""
    return 'pong'

from django.core import mail
from django.conf import settings
@app.task(bind=True)
def get_outbox(self):
    print(settings.EMAIL_BACKEND)
    print(mail.outbox)
    return mail.outbox



