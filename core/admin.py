from django.contrib import admin
from reversion.models import Version

from . import models

# Register with admin
admin.site.register(models.FailedTask)
admin.site.register(Version)

