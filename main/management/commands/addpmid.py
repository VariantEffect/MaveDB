import sys
from django.core.management.base import BaseCommand

from urn.models import get_model_by_urn
from metadata.models import PubmedIdentifier
from metadata.validators import validate_pubmed_identifier


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--urn", type=str, help="Dataset URN")
        parser.add_argument("--pmid", type=str, help="PubMed identifier")

    def handle(self, *args, **kwargs):
        urn = kwargs.get("urn", None)
        if not urn:
            raise ValueError("A valid URN is required.")

        pmid = kwargs.get("pmid", None)
        if not pmid:
            raise ValueError("A PubMed ID is required.")
        validate_pubmed_identifier(pmid)

        pmid_instance, created = PubmedIdentifier.objects.get_or_create(
            identifier=pmid
        )
        instance = get_model_by_urn(urn)
        instance.pubmed_ids.add(pmid_instance)
        instance.save()
        sys.stdout.write("Added PMID {} to {}.\n".format(pmid, instance))
