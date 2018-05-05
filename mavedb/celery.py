import time
from celery import Celery
from django.conf import settings

try:
    settings.configure()
except RuntimeError:
    # settings already configured
    pass

app = Celery('mavedb')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object(settings)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print("Started at {}.".format(time.time()))
    print('Request: {0!r}'.format(self.request))
