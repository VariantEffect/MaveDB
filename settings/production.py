# settings/production.py
from .base import *

DEBUG = False
PRODUCTION = True
ADMIN_ENABLED = not DEBUG

USE_SOCIAL_AUTH = True

os.environ.setdefault('PYPANDOC_PANDOC', '/usr/local/bin/pandoc')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'www.mavedb.org',]


# Email these users whenever an exception is raised causing a 500 error.
# This will email the stack trace.
ADMINS = [
    ('Alan', 'alan.rubin@wehi.edu.au'),
    ('Daniel', 'esposito.d@wehi.edu.au')
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Los_Angeles'
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
        "HOST": get_secret('database_host'),
        "PORT": get_secret('database_port'),
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
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/data/mavedb_project/mavedb/info.log',
            'formatter': 'verbose'
        },
        'celery': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/data/mavedb_project/mavedb/celery.log',
            'formatter': 'verbose'
        },
        'core.tasks': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/data/mavedb_project/mavedb/celery_core_tasks.log',
            'formatter': 'verbose'
        },
        'accounts.tasks': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/data/mavedb_project/mavedb/celery_accounts_tasks.log',
            'formatter': 'verbose'
        },
        'dataset.tasks': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/data/mavedb_project/mavedb/celery_dataset_tasks.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True
        },
        'celery': {
            'handlers': ['celery'],
            'level': 'ERROR',
            'propagate': True
        },
        'core.tasks': {
            'handlers': ['core.tasks'],
            'level': 'ERROR',
            'propagate': True
        },
        'accounts.tasks': {
            'handlers': ['accounts.tasks'],
            'level': 'ERROR',
            'propagate': True
        },
        'dataset.tasks': {
            'handlers': ['dataset.tasks'],
            'level': 'ERROR',
            'propagate': True
        },
    },
}


# Email setup
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


# ------ CELERY CONFIG ------------------- #
# Celery needs these in each settings file
DATASET_TASK_SOFT_TIME_LIMIT =  12 * 60 * 60  # 12 hours in seconds
broker_url = 'amqp://localhost:5672//'
accept_content = ('json',)
result_serializer = 'json'

task_ignore_result = True
task_serializer = 'json'
worker_hijack_root_logger = False
task_soft_time_limit = 60  # seconds
task_always_eager = False
task_create_missing_queues = True

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