import sys
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.factories import UserFactory

from metadata.models import UniprotOffset, RefseqOffset, EnsemblOffset

from dataset import factories, utilities
from genome import factories as genome_factories
from genome import models as genome_models
from variant.models import Variant
from dataset import constants

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        password = "1234qwer"
        with transaction.atomic():
            for i in range(40):
                username = "user-{}".format(i + 1)
                user = UserFactory(username=username)
                if username == "user-1":
                    user.is_superuser = True
                    user.is_staff = True
                user.set_password(password)
                user.save()
                instance = factories.ExperimentFactory()
                statuses = [True] * 4 + [False] * 2
                for _ in statuses:
                    # Configure the scoreset first.
                    scoreset = factories.ScoreSetFactory(
                        experiment=instance,
                        dataset_columns={
                            constants.score_columns: [
                                "score1",
                                "score2",
                                "score3",
                                "score4",
                                "score5",
                                "score6",
                            ],
                            constants.count_columns: [
                                "count1",
                                "count2",
                                "count3",
                                "count4",
                            ],
                        },
                    )
                    variants = []
                    for n in range(3000):
                        variants.append(
                            {
                                "hgvs_nt": "c.{}{}>{}".format(
                                    n + 1,
                                    random.choice("ATCG"),
                                    random.choice("ATCG"),
                                ),
                                "hgvs_pro": "c.{}{}>{}".format(
                                    n + 1,
                                    random.choice("ATCG"),
                                    random.choice("ATCG"),
                                ),
                                "data": {
                                    constants.variant_score_data: {
                                        "score1": random.random(),
                                        "score2": random.random(),
                                        "score3": random.random(),
                                        "score4": random.random(),
                                        "score5": random.random(),
                                        "score6": random.random(),
                                    },
                                    constants.variant_count_data: {
                                        "count1": random.randint(a=1, b=1000),
                                        "count2": random.randint(a=1, b=1000),
                                        "count3": random.randint(a=1, b=1000),
                                        "count4": random.randint(a=1, b=1000),
                                    },
                                },
                            }
                        )
                    Variant.bulk_create(
                        parent=scoreset, variant_kwargs_list=variants
                    )
                    target = genome_factories.TargetGeneFactory(
                        scoreset=scoreset
                    )
                    genomes = genome_models.ReferenceGenome.objects.all()
                    genome_factories.ReferenceMapFactory(
                        target=target,
                        genome=random.choice(genomes),
                        is_primary=True,
                    )
                    target.scoreset = scoreset
                    target.save()
                    scoreset.save()

                for scoreset, publish in zip(
                    instance.children.all(), statuses
                ):
                    UniprotOffset.objects.create(
                        offset=i * 3 + 1,
                        target=scoreset.target,
                        identifier=scoreset.target.uniprot_id,
                    )
                    RefseqOffset.objects.create(
                        offset=i * 3 + 2,
                        target=scoreset.target,
                        identifier=scoreset.target.refseq_id,
                    )
                    EnsemblOffset.objects.create(
                        offset=i * 3 + 3,
                        target=scoreset.target,
                        identifier=scoreset.target.ensembl_id,
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
                            scoreset.urn,
                            scoreset.target,
                            scoreset.target.reference_maps.first().genome,
                        )
                    )

                sys.stdout.write("Created {}\n".format(instance.urn))
