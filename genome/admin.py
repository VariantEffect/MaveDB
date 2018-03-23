from django.contrib import admin

from .models import (
    TargetOrganism, TargetGene, ReferenceGenome, WildTypeSequence
)

admin.site.register(TargetOrganism)
admin.site.register(TargetGene)
admin.site.register(ReferenceGenome)
admin.site.register(WildTypeSequence)

