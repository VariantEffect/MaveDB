from django.contrib import admin

from .models import (
    TargetGene, WildTypeSequence, Annotation, ReferenceGenome, Interval
)

admin.site.register(TargetGene)
admin.site.register(WildTypeSequence)
admin.site.register(Annotation)
admin.site.register(ReferenceGenome)
admin.site.register(Interval)
