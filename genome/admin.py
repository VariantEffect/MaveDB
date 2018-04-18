from django.contrib import admin

from .models import (
    TargetGene, WildTypeSequence, ReferenceMap, ReferenceGenome, Interval
)

admin.site.register(TargetGene)
admin.site.register(WildTypeSequence)
admin.site.register(ReferenceMap)
admin.site.register(ReferenceGenome)
admin.site.register(Interval)
