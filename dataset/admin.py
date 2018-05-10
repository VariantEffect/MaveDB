import reversion

from django.contrib import admin

from .models.experimentset import ExperimentSet
from .models.experiment import Experiment
from .models.scoreset import ScoreSet


# admin.site.register(ExperimentSet)
# admin.site.register(Experiment)
# admin.site.register(ScoreSet)

reversion.register(
    model=ExperimentSet,
    fields=ExperimentSet.tracked_fields(),
)

reversion.register(
    model=Experiment,
    fields=Experiment.tracked_fields(),
)

reversion.register(
    model=ScoreSet,
    fields=ScoreSet.tracked_fields(),
)
