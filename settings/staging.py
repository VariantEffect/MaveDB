# settings/staging.py
from .base import *

DEBUG = False
STAGING = True
ADMIN_ENABLED = DEBUG

USE_SOCIAL_AUTH = True

os.environ.setdefault("PYPANDOC_PANDOC", "/usr/local/bin/pandoc")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", ".compute.amazonaws.com"]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Australia/Melbourne"
USE_I18N = True
USE_L10N = True
USE_TZ = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "mavedb",
        "USER": get_secret("database_user"),
        "PASSWORD": get_secret("database_password"),
        "HOST": "localhost",
        "PORT": "",
    }
}

# Set up logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(levelname)s] %(asctime)s %(module)s %(message)s"
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/www/mavedb/logs/mavedb.log",
            "formatter": "verbose",
        },
        "celery": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/www/mavedb/logs/celery.log",
            "formatter": "verbose",
        },
        "core.tasks": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/www/mavedb/logs/celery_core_tasks.log",
            "formatter": "verbose",
        },
        "accounts.tasks": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/www/mavedb/logs/celery_accounts_tasks.log",
            "formatter": "verbose",
        },
        "dataset.tasks": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "/var/www/mavedb/logs/celery_dataset_tasks.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["file"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["celery"], "level": "INFO", "propagate": True},
        "core.tasks": {
            "handlers": ["core.tasks"],
            "level": "INFO",
            "propagate": True,
        },
        "accounts.tasks": {
            "handlers": ["accounts.tasks"],
            "level": "INFO",
            "propagate": True,
        },
        "dataset.tasks": {
            "handlers": ["dataset.tasks"],
            "level": "INFO",
            "propagate": True,
        },
    },
}


# ------ CELERY CONFIG ------------------- #
# Celery needs these in each settings file
CELERY_TASK_SOFT_TIME_LIMIT = 7 * 24 * 60 * 60  # 7 days
CELERY_TASK_TIME_LIMIT = CELERY_TASK_SOFT_TIME_LIMIT
CELERY_BROKER_URL = "amqp://localhost:5672//"
CELERY_ACCEPT_CONTENT = ("pickle", "application/x-python-serialize", "json")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TASK_IGNORE_RESULT = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_COMPRESSION = "gzip"


# Celery needs this for autodiscover to work
INSTALLED_APPS = [
    "metadata",
    "main",
    "genome",
    "urn",
    "variant",
    "dataset",
    "search",
    "api",
    "accounts",
    "core",
    "guardian",
    "reversion",
    "social_django",
    "django_extensions",
    "widget_tweaks",
    "rest_framework",
    "django_filters",
    "tracking",
    "import_export",
    "mod_wsgi.server",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
