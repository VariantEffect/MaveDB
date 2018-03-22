# settings/local.py

from .base import *

DEBUG = True

USE_SOCIAL_AUTH = False

os.environ.setdefault('PYPANDOC_PANDOC', '/anaconda/bin/pandoc')

ALLOWED_HOSTS = ['localhost', '127.0.0.1',]

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

# Set up logging
LOGGING = {
   ‘version’: 1,
   ‘disable_existing_loggers’: False,
   ‘formatters’: {
       ‘verbose’: {
           ‘format’: ‘[%(levelname)s] %(asctime)s %(module)s %(message)s’
       },
       ‘simple’: {
           ‘format’: ‘%(levelname)s %(message)s’
       },
   },
   ‘handlers’: {
       ‘file’: {
           ‘level’: ‘WARNING’,
           ‘class’: ‘logging.FileHandler’,
           ‘filename’: ‘./info.log’,
           ‘formatter’: ‘verbose’
       },
   },
   ‘loggers’: {
       ‘django’: {
           ‘handlers’: [‘file’],
           ‘level’: ‘WARNING’,
           ‘propagate’: True
       },
   },
}
