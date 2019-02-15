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
            '--urns',
            nargs='+',
            type=str,
            help="Score set urns to re-number.",
        )
        parser.add_argument(
            '--all',
            action='store_true',
            dest='all',
            help="Reset numbering on all score sets.",
        )
    
    @transaction.atomic
    def handle(self, *args, **kwargs):
        urns = kwargs.get('urns', [])
        all_ = kwargs.get('all', False)
        
        if all_:
            scoresets = ScoreSet.objects.all()
        else:
            scoresets = ScoreSet.objects.filter(urn__in=urns)
            
        for scoreset in scoresets:
            if scoreset.private:
                scoreset.last_child_value = 0
                scoreset.save()
                sys.stdout.write("{} is private. Skipping.\n\n".format(
                    scoreset.urn))
                continue
                
            sys.stdout.write("Re-numbering {}.\n".format(scoreset.urn))

            scoreset.last_child_value = 0
            variants = sorted(
                scoreset.children.all(),
                key=lambda v: get_number(v)
            )
            urns = Variant.bulk_create_urns(scoreset.children.count(), scoreset)
            sys.stdout.write("\tCreated urns {}, ..., {}.\n".format(
                ', '.join(urns[0:3]), urns[-1]))
    
            sys.stdout.write("\tUpdating variant urns.\n")
            for urn, variant in zip(urns, variants):
                variant.urn = urn
                variant.save()
    
            scoreset.last_child_value = len(variants)
            scoreset.save()
            sys.stdout.write('\tUpdated last child value to {}.\n\n'.format(
                scoreset.last_child_value))
