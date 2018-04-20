import os
import json

from django.conf import settings

from genome.models import ReferenceGenome
from metadata.models import EnsemblIdentifier, RefseqIdentifier

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.GENOME_DIR, 'reference_genomes.json')
        with open(path, 'rt') as fp:
            references = json.load(fp)
            for reference, params in references.items():
                ensembl_id = params['ensembl_id']
                refseq_id = params['refseq_id']
                ensembl_id, _ = EnsemblIdentifier.objects.get_or_create(
                    identifier=ensembl_id
                )
                refseq_id, _ = RefseqIdentifier.objects.get_or_create(
                    identifier=refseq_id
                )
                params['ensembl_id'] = ensembl_id
                params['refseq_id'] = refseq_id
                ReferenceGenome.objects.create(**params)
