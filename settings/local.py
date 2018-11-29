# settings/local.py
from .base import *

DEBUG = True
LOCAL = True
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
task_soft_time_limit = 7 * 24 * 60 * 60  # 7 days
task_time_limit = task_soft_time_limit
broker_url = 'amqp://localhost:5672//'
accept_content = ('pickle', 'application/x-python-serialize', 'json')
task_serializer = 'json'
result_serializer = 'json'

task_ignore_result = True
worker_hijack_root_logger = False
task_always_eager = True
task_create_missing_queues = True