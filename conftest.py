import pytest

"""
@pytest.fixture(scope='session')
def celery_config():
    return {
        'task_always_eager': True,
        'task_time_limit': 10,
        'broker_connection_timeout': 9,
        'broker_url': "amqp://guest:guest@localhost:5672/test_rink",
        'result_backend': "amqp://guest:guest@localhost:5672/test_rink",
    }
"""

@pytest.fixture(autouse=True)
def enable_db_access(db):
    pass
