import os
import sys
import json

from django.conf import settings

from genome.models import ReferenceGenome
from metadata.models import GenomeIdentifier

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = os.path.join(settings.GENOME_DIR, "reference_genomes.json")
        with open(path, "rt") as fp:
            references = json.load(fp)
            for reference_attrs in references:
                name = reference_attrs["short_name"]
                organism_name = reference_attrs["organism_name"]
                assembly_params = reference_attrs["assembly_identifier"] or {}
                accession = assembly_params.get("identifier", None)

                # Only create ReferenceGenome instance if it does not exist.
                if not ReferenceGenome.objects.filter(short_name=name).count():
                    genome_identifier = None
                    if accession:
                        genome_identifier, _ = GenomeIdentifier.objects.get_or_create(
                            identifier=accession
                        )
                    params = {
                        "short_name": name,
                        "organism_name": organism_name,
                        "genome_id": genome_identifier,
                    }
                    sys.stdout.write("Created reference '%s'\n" % name)
                    ReferenceGenome.objects.create(**params)
                else:
                    sys.stdout.write("Reference '%s' already exists\n" % name)
