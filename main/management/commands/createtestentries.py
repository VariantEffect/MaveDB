import sys

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.factories import UserFactory
from accounts.permissions import assign_user_as_instance_admin

from metadata.models import (
    UniprotOffset, RefseqOffset, EnsemblOffset
)

from dataset.factories import ExperimentWithScoresetFactory
from variant.factories import VariantFactory


User = get_user_model()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('clear', nargs='?', type=bool, default=False)

    def handle(self, *args, **kwargs):
        password = "1234qwer"
        with transaction.atomic():
            for i, username in enumerate(['usera', 'userb', 'userc', 'userd']):
                user = UserFactory(username=username)
                user.set_password(password)
                user.save()
                instance = ExperimentWithScoresetFactory()
                assign_user_as_instance_admin(user, instance)
                assign_user_as_instance_admin(user, instance.parent)
                for scoreset in instance.children.all():
                    UniprotOffset.objects.create(
                        offset=i*3 + 1,
                        target=scoreset.target,
                        identifier=scoreset.target.uniprot_id
                    )
                    RefseqOffset.objects.create(
                        offset=i*3 + 2,
                        target=scoreset.target,
                        identifier=scoreset.target.refseq_id
                    )
                    EnsemblOffset.objects.create(
                        offset=i*3 + 3,
                        target=scoreset.target,
                        identifier=scoreset.target.ensembl_id
                    )

                    assign_user_as_instance_admin(user, scoreset)
                    scoreset.publish(propagate=True)
                    scoreset.set_modified_by(user, propagate=True)
                    scoreset.set_created_by(user, propagate=True)
                    for i in range(10):
                        VariantFactory(scoreset=scoreset)

                    scoreset.save(save_parents=True)

                sys.stdout.write("Created {}\n".format(instance.urn))
