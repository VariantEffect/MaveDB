from django.contrib import admin

from reversion.admin import VersionAdmin

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet, Variant

from .models import News, SiteInformation
from .models import Keyword, ExternalAccession, TargetOrganism
from .models import ReferenceMapping


# Register with admin
admin.site.register(News)
admin.site.register(SiteInformation)

admin.site.register(TargetOrganism)
admin.site.register(Keyword)
admin.site.register(ExternalAccession)
admin.site.register(ReferenceMapping)


admin.site.register(Variant)


@admin.register(ExperimentSet)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(Experiment)
class YourModelAdmin(VersionAdmin):
    pass


@admin.register(ScoreSet)
class YourModelAdmin(VersionAdmin):
    pass
