import pytest

@pytest.fixture(scope='session')
def celery_config():
    return {
        'task_always_eager': True,
        'task_time_limit': 10,
        'redis_socket_connect_timeout': 10,
        'redis_socket_timeout': 8,
        'broker_connection_timeout': 9,
        #'broker_url': "amqp://guest:guest@localhost:5672/test_rink",
    }

@pytest.fixture(autouse=True)
def enable_db_access(db):
    pass