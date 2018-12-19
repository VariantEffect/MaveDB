import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from dataset.models.scoreset import ScoreSet
from variant.models import Variant

def get_number(variant):
    return int(variant.urn.split('#')[-1])


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--urn', type=str, help="Dataset URN",)
    
    @transaction.atomic
    def handle(self, *args, **kwargs):
        urn = kwargs.get('urn', None)
        if urn:
            scoreset = ScoreSet.objects.get(urn=urn)
        else:
            raise ValueError("A valid URN is required.")

        scoreset.last_child_value = 0
        variants = sorted(scoreset.children.all(), key=lambda v: get_number(v))
        urns = Variant.bulk_create_urns(scoreset.children.count(), scoreset)
        sys.stdout.write("Saved urns {}, ..., {}.\n".format(
            ', '.join(urns[0:3]), urns[-1]))
        
        for urn, variant in zip(urns, variants):
            variant.urn = urn
            variant.save()
        
        scoreset.last_child_value = len(variants)
        scoreset.save()
        sys.stdout.write('Updated last child value to {}.\n'.format(
            scoreset.last_child_value))
