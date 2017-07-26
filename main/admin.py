from django.contrib import admin

from .models import News, SiteInformation

admin.site.register(News)
admin.site.register(SiteInformation)
