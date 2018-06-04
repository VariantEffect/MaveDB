# settings/staging.py
from .base import *

DEBUG = False
ADMIN_ENABLED = DEBUG

USE_SOCIAL_AUTH = True

os.environ.setdefault('PYPANDOC_PANDOC', '/usr/local/bin/pandoc')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '.compute.amazonaws.com',]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Melbourne'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Extend the base installed_apps with any extra requirements
INSTALLED_APPS.extend([
    'mod_wsgi.server'
])

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mavedb",
        "USER": get_secret('database_user'),
        "PASSWORD": get_secret('database_password'),
        "HOST": "localhost",
        "PORT": "",
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
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/usr/local/webapps/logs/mavedb.log',
            'formatter': 'verbose'
        },
        'celery': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/usr/local/webapps/logs/celery.log',
            'formatter': 'verbose'
        },
        'core.tasks': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/usr/local/webapps/logs/celery_core_tasks.log',
            'formatter': 'verbose'
        },
        'accounts.tasks': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/usr/local/webapps/logs/celery_accounts_tasks.log',
            'formatter': 'verbose'
        },
        'dataset.tasks': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/usr/local/webapps/logs/celery_dataset_tasks.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False
        },
        'celery': {
            'handlers': ['celery'],
            'level': 'DEBUG',
            'propagate': False
        },
        'core.tasks': {
            'handlers': ['core.tasks'],
            'level': 'DEBUG',
            'propagate': False
        },
        'accounts.tasks': {
            'handlers': ['accounts.tasks'],
            'level': 'DEBUG',
            'propagate': False
        },
        'dataset.tasks': {
            'handlers': ['dataset.tasks'],
            'level': 'DEBUG',
            'propagate': False
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