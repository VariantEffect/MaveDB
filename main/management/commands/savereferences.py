import os
import json

from django.conf import settings

from genome.serializers import ReferenceGenomeSerializer
from genome.models import ReferenceGenome

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.GENOME_DIR, 'reference_genomes.json')
        with open(path, 'wt') as fp:
            data = ReferenceGenomeSerializer(
                ReferenceGenome.objects.all(), many=True).data
            json.dump(data, fp, indent=4, sort_keys=True)
