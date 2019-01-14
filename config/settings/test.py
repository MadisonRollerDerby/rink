"""
With these settings, tests run faster.
"""

from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# False in production?

URL_DOMAIN = env("URL_DOMAIN", default="http://localhost:8000")


# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env('DJANGO_SECRET_KEY', default='mMW4rrhtezQvDPIOn61KGnZmHLNTxFzqXQ7kVjykwT1L3ujQ3A6qLEjni9te1y6F')
# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
#TEST_RUNNER = "celery.contrib.test_runner.CeleryTestSuiteRunner"
# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG  # noqa F405
TEMPLATES[0]['OPTIONS']['loaders'] = [  # noqa F405
    (
        'django.template.loaders.cached.Loader',
        [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ],
    ),
]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
#EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = '/tmp/test-emails' # change this to a proper location
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = 'localhost'
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# Your stuff...
# ------------------------------------------------------------------------------
STRIPE_TEST_SECRET="sk_test_JUmsyjIU3JTkQgmLL0sasu0z"
STRIPE_TEST_PUBLIC="pk_test_ewB0eFxUAWV0cMJEV2UJcHJQ"

STRIPE_API_VERSION = '2018-11-08'
