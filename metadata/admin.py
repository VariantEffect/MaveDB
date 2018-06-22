from django.contrib import admin

from .import models

# Register your models here.
admin.site.register(models.Keyword)
admin.site.register(models.PubmedIdentifier)
admin.site.register(models.DoiIdentifier)
admin.site.register(models.SraIdentifier)
