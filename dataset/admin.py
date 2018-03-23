from django.contrib import admin
from reversion.admin import VersionAdmin

from .models import ExperimentSet, Experiment, ScoreSet


@admin.register(ExperimentSet)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(Experiment)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(ScoreSet)
class YourModelAdmin(VersionAdmin):
    pass
