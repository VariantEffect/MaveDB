import os
import json

from django.conf import settings

from genome.models import ReferenceGenome
from metadata.models import GenomeIdentifier

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.GENOME_DIR, 'reference_genomes.json')
        with open(path, 'rt') as fp:
            references = json.load(fp)
            for reference, params in references.items():
                if not ReferenceGenome.objects.filter(
                        short_name=reference).count():
                    genome_id = params['genome_id']
                    if genome_id:
                        genome_id, _ = GenomeIdentifier.objects.get_or_create(
                            identifier=genome_id
                        )
                    params['genome_id'] = genome_id
                    ReferenceGenome.objects.create(**params)
