import sys
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.factories import UserFactory

from metadata.models import (
    UniprotOffset, RefseqOffset, EnsemblOffset
)

from dataset import factories, utilities
from genome import factories as genome_factories
from genome import models  as genome_models
from variant.factories import VariantFactory

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        password = "1234qwer"
        with transaction.atomic():
            for i, username in enumerate(['usera', 'userb', 'userc', 'userd']):
                user = UserFactory(username=username)
                if username == 'usera':
                    user.is_superuser = True
                    user.is_staff = True
                user.set_password(password)
                user.save()
                instance = factories.ExperimentFactory()
                for _ in [False, True]:
                    # Configure the scoreset first.
                    scoreset = factories.ScoreSetFactory(experiment=instance)
                    for _ in range(100):
                        VariantFactory(scoreset=scoreset)
                    target = genome_factories.TargetGeneFactory(scoreset=scoreset)
                    genomes = genome_models.ReferenceGenome.objects.all()
                    genome_factories.ReferenceMapFactory(
                        target=target,
                        genome=random.choice(genomes),
                        is_primary=True
                    )
                    target.scoreset = scoreset
                    target.save()
                    scoreset.save()
                
                for scoreset, publish in zip(
                        instance.children.all(), [True, False]):
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

                    if publish:
                        scoreset = utilities.publish_dataset(scoreset)

                    scoreset.set_modified_by(user, propagate=True)
                    scoreset.set_created_by(user, propagate=True)
                    scoreset.save()
                    
                    experiment = scoreset.parent
                    experiment.refresh_from_db()
                    experiment.save()
                    
                    experimentset = experiment.experimentset
                    experimentset.refresh_from_db()
                    experimentset.save()

                    scoreset.add_administrators(user)
                    scoreset.experiment.add_administrators(user)
                    scoreset.experiment.experimentset.add_administrators(user)
                    
                    sys.stdout.write(
                        "Created {} with target {} and genome {}\n".format(
                            scoreset.urn, scoreset.target,
                            scoreset.target.reference_maps.first().genome)
                    )

                sys.stdout.write("Created {}\n".format(instance.urn))
