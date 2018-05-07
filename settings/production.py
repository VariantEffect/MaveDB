# settings/production.py

from .base import *

DEBUG = False

USE_SOCIAL_AUTH = True

os.environ.setdefault('PYPANDOC_PANDOC', '/usr/local/bin/pandoc')

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'www.mavedb.org',]

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
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True
        },
    },
}