import sys
from django.core.management.base import BaseCommand

from urn.models import get_model_by_urn


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--urn', type=str, help="Dataset URN",)

    def handle(self, *args, **kwargs):
        urn = kwargs.get('urn', None)
        if urn:
            instance = get_model_by_urn(urn)
        else:
            raise ValueError("A valid URN is required.")

        while instance:
            if not instance.has_public_urn:
                instance.private = True
                instance.save()
                sys.stderr.write("Set {} to private.\n".format(instance))
            instance = instance.parent
