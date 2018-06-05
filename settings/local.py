# settings/local.py
from .base import *

DEBUG = True
ADMIN_ENABLED = DEBUG

USE_SOCIAL_AUTH = False

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Melbourne'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mavedb",
        "USER": "mave_admin",
        "PASSWORD": "abc123",
        "HOST": "localhost",
        "PORT": "",
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Set up logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s] %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/info.log',
            'formatter': 'verbose'
        },
        'celery': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/celery.log',
            'formatter': 'verbose'
        },
        'core.tasks': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/celery_core_tasks.log',
            'formatter': 'verbose'
        },
        'accounts.tasks': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/celery_accounts_tasks.log',
            'formatter': 'verbose'
        },
        'dataset.tasks': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/celery_dataset_tasks.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False
        },
        'celery': {
            'handlers': ['celery'],
            'level': 'INFO',
            'propagate': True
        },
        'core.tasks': {
            'handlers': ['core.tasks'],
            'level': 'INFO',
            'propagate': True
        },
        'accounts.tasks': {
            'handlers': ['accounts.tasks'],
            'level': 'INFO',
            'propagate': True
        },
        'dataset.tasks': {
            'handlers': ['dataset.tasks'],
            'level': 'INFO',
            'propagate': True
        },
    },
}

# ------ CELERY CONFIG ------------------- #
# Celery needs these in each settings file
broker_url = 'amqp://localhost:5672//'
task_ignore_result = True
worker_hijack_root_logger = False

task_serializer = 'json'
accept_content = ('json',)
result_serializer = 'json'

task_always_eager = True
task_create_missing_queues = True
task_routes = {
    'dataset.tasks.*': {'queue': 'long'},
    'core.tasks.*': {'queue': 'quick'},
    'accounts.tasks.*': {'queue': 'quick'},
}

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

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]