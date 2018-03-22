# settings/local.py

from .base import *

os.environ.setdefault('PYPANDOC_PANDOC', '/anaconda/bin/pandoc')

ALLOWED_HOSTS = ['localhost', '127.0.0.1',]

TIME_ZONE = 'Australia/Melbourne'

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
