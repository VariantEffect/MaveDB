import reversion
from reversion.admin import VersionAdmin

from django.contrib import admin

from . import models

reversion.register(
    model=models.experimentset.ExperimentSet,
    fields=models.experimentset.ExperimentSet.tracked_fields(),
)

reversion.register(
    model=models.experiment.Experiment,
    fields=models.experiment.Experiment.tracked_fields(),
)

reversion.register(
    model=models.scoreset.ScoreSet,
    fields=models.scoreset.ScoreSet.tracked_fields(),
)


# The following classes enable version control to be accessed from the admin
# view
@admin.register(models.experiment.Experiment)
class ExperimentVersion(VersionAdmin):
    pass


@admin.register(models.experimentset.ExperimentSet)
class ExperimentSetVersion(VersionAdmin):
    pass


@admin.register(models.scoreset.ScoreSet)
class ScoreSetVersion(VersionAdmin):
    pass


