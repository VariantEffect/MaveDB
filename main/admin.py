from django.conf import settings
from django.contrib import admin
from django.db.models import ObjectDoesNotExist

from reversion.admin import VersionAdmin

from dataset.models import Experiment, ExperimentSet
from metadata.models import Keyword, ExternalIdentifier
from genome.models import TargetOrganism
from dataset.models import ScoreSet
from variant.models import Variant

from .models import News, SiteInformation, Licence


# Register with admin
admin.site.register(News)
admin.site.register(Licence)
admin.site.register(SiteInformation)

admin.site.register(TargetOrganism)
admin.site.register(Keyword)
admin.site.register(ExternalIdentifier)


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
