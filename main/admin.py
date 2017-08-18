from django.contrib import admin

from .models import News, SiteInformation

admin.site.register(News)
admin.site.register(SiteInformation)

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet, Variant

# Register your models here.
admin.site.register(ExperimentSet)
admin.site.register(Experiment)
admin.site.register(ScoreSet)
admin.site.register(Variant)
