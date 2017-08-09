from django.contrib import admin

from .models import News, SiteInformation

admin.site.register(News)
admin.site.register(SiteInformation)

from experiment.models import Experiment

# Register your models here.
admin.site.register(Experiment)
