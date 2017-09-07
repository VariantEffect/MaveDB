from django.contrib import admin

from reversion.admin import VersionAdmin

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet, Variant

from .models import News, SiteInformation
from .models import Keyword, ExternalAccession, TargetOrganism
from .models import ReferenceMapping


@admin.register(News)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(SiteInformation)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(ExperimentSet)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(Experiment)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(ScoreSet)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(Variant)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(Keyword)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(ExternalAccession)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(TargetOrganism)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(ReferenceMapping)
class YourModelAdmin(VersionAdmin):
    pass
