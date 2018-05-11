from django.contrib import admin

from . import models

# Register with admin
admin.site.register(models.News)
admin.site.register(models.Licence)
admin.site.register(models.SiteInformation)





