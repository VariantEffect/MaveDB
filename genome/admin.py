import reversion

from django.contrib import admin

from .models import (
    TargetGene, WildTypeSequence, ReferenceMap, ReferenceGenome, GenomicInterval
)

# admin.site.register(TargetGene)
# admin.site.register(WildTypeSequence)
# admin.site.register(ReferenceMap)
# admin.site.register(ReferenceGenome)
# admin.site.register(GenomicInterval)

reversion.register(TargetGene)
reversion.register(WildTypeSequence)
reversion.register(ReferenceMap)
reversion.register(ReferenceGenome)
reversion.register(GenomicInterval)
