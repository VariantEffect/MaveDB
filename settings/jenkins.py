# settings/jenkins.py
import logging

from .staging import *

# Disable logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
}
logging.disable(logging.CRITICAL)


# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
   }
}


# ------ CELERY CONFIG ------------------- #
# Celery needs these in each settings file
CELERY_TASK_SOFT_TIME_LIMIT = 7 * 24 * 60 * 60  # 7 days
CELERY_TASK_TIME_LIMIT = CELERY_TASK_SOFT_TIME_LIMIT
CELERY_BROKER_URL = 'amqp://localhost:5672//'
CELERY_ACCEPT_CONTENT = ('pickle', 'application/x-python-serialize', 'json')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_TASK_IGNORE_RESULT = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_COMPRESSION = 'gzip'

# Celery needs this for autodiscover to work
INSTALLED_APPS = [
    'metadata',
    'main',
    'genome',
    'urn',
    'variant',
    'dataset',
    'search',
    'api',
    'accounts',
    'core',

    'guardian',
    'reversion',
    'social_django',
    'django_extensions',
    'widget_tweaks',
    'rest_framework',
    'django_filters',
    'tracking',
    'import_export',
    'mod_wsgi.server',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
