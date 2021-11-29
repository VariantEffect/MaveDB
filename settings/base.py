# settings/base.py
import os

# Set path for pypandoc
os.environ.setdefault("PYPANDOC_PANDOC", "/usr/bin/pandoc")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_HOSTS = os.getenv("APP_ALLOWED_HOSTS", "127.0.0.1 localhost").split(
    " "
)

# Security settings
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# MaveDB APP behaviour settings
META_ANALYSIS_ALLOW_DAISY_CHAIN = False

BASE_URL = os.getenv("APP_BASE_URL", "localhost:8000")
API_BASE_URL = os.getenv("APP_API_BASE_URL", "localhost:8000/api")
SECRET_KEY = os.getenv("APP_SECRET_KEY", "very_secret_key")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
MAIN_DIR = BASE_DIR + "/data/main/"
GENOME_DIR = BASE_DIR + "/data/genome/"

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv("APP_DB_NAME", "mavedb"),
        "USER": os.getenv("APP_DB_USER", "mave_admin"),
        "PASSWORD": os.getenv("APP_DB_PASSWORD", "abc123"),
        "HOST": os.getenv("APP_DB_HOST", "localhost"),
        "PORT": os.getenv("APP_DB_PORT", "5432"),
    }
}

# Social auth settings for ORCID authentication
SOCIAL_AUTH_ORCID_PROFILE_EXTRA_PARAMS = {"credit-name": "credit_name"}
SOCIAL_AUTH_ORCID_KEY = os.getenv("APP_ORCID_KEY", None)
SOCIAL_AUTH_ORCID_SECRET = os.getenv("APP_ORCID_SECRET", None)
SOCIAL_AUTH_USER_MODEL = "auth.User"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/profile/"
SOCIAL_AUTH_LOGIN_ERROR_URL = "/profile/error/"
SOCIAL_AUTH_URL_NAMESPACE = "accounts:social"
SOCIAL_AUTH_PIPELINE = [
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    # 'social_core.pipeline.social_auth.load_extra_data',
    # adds credit-name as credit_name to extra data in the social auth
    # profile model
    "core.pipeline.mave_load_extra_data",
    "social_core.pipeline.user.user_details",
    "social_core.pipeline.social_auth.associate_by_email",
]


# Application definition
INSTALLED_APPS = [
    "manager",
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
    "rest_framework.authtoken",
    "django_filters",
    "tracking",
    "import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",  # this is default
    "guardian.backends.ObjectPermissionBackend",
    "social_core.backends.orcid.ORCIDOAuth2",
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "tracking.middleware.VisitorTrackingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Social-auth middleware
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "mavedb.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Custom
                "main.context_processors.baseurl",
                "main.context_processors.site_information",
                # Social-auth context_processors
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ]
        },
    }
]

WSGI_APPLICATION = "mavedb.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
DOCS_STATIC_DIR = BASE_DIR + "/docs/build/"

STATIC_URL = "/static/"
STATICFILES_DIRS = [DOCS_STATIC_DIR]
STATIC_ROOT = os.path.abspath(os.path.join(BASE_DIR, "static"))
MAVEDB_DOCS_ROOT = STATIC_ROOT + "/docs/mavedb/html"
MAVEHGVS_DOCS_ROOT = STATIC_ROOT + "/docs/mavehgvs/html"
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800

# Redirect to home URL after login (Default redirects to /profile/)
LOGIN_REDIRECT_URL = "/profile/"
LOGOUT_REDIRECT_URL = "/"

# DEBUG email server, set to something proper when DEBUG = FALSE
DEFAULT_FROM_EMAIL = "mavedb@mavedb.org"
SERVER_EMAIL = "admin@mavedb.org"
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Host for sending e-mail
# EMAIL_HOST = 'localhost'
# EMAIL_PORT = 1025

# Reply-to email for user emails
# REPLY_TO_EMAIL = os.environ.get("MAVEDB_REPLY_TO_EMAIL", '')
REPLY_TO_EMAIL = "alan.rubin@wehi.edu.au"

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "1000/day", "user": "1000/day"},
}


# Django-tracking2 settings
TRACK_AJAX_REQUESTS = True
TRACK_ANONYMOUS_USERS = True
TRACK_SUPERUSERS = True
TRACK_PAGEVIEWS = True
TRACK_USING_GEOIP = False
TRACK_REFERER = True
TRACK_QUERY_STRING = True
TRACK_IGNORE_STATUS_CODES = [400, 404, 403, 405, 410, 500]
TRACK_IGNORE_URLS = [
    # Admin
    r"admin/.*",
    # Static pages
    r"^(favicon\.ico|robots\.txt)$",
    r"^terms_privacy/$",
    r"^contact/$",
    r"^docs/$",
    # Profile/Account
    r"^profile/.*",
    r"^register/$",
    r"^login/.*",
    r"^logout/.*",
    # OAuth
    r"^oauth/.*",
    r"^complete/.*",
    r"^disconnect/.*",
    # Django-tracking2
    r"^tracking/.*",
]
