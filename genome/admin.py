from django.contrib import admin

from . import models

admin.site.register(models.TargetGene)
admin.site.register(models.WildTypeSequence)
admin.site.register(models.ReferenceMap)
admin.site.register(models.ReferenceGenome)
admin.site.register(models.GenomicInterval)
