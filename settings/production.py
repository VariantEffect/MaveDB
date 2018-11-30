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
            'level': 'INFO',
            'propagate': True
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


# Email setup
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


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
CELERY_TASK_ALWAYS_EAGER = False
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

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]