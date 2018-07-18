import datetime

from django.db import transaction

from dataset import models
from variant.models import Variant

from .models.experimentset import ExperimentSet
from .models.experiment import Experiment
from .models.scoreset import ScoreSet


@transaction.atomic
def delete_instance(instance):
    if isinstance(instance, ExperimentSet):
        delete_experimentset(instance)
    elif isinstance(instance, Experiment):
        delete_experiment(instance)
    elif isinstance(instance, ScoreSet):
        delete_scoreset(instance)
    else:
        raise TypeError(
            "Expected ExperimentsSet, Experiment or ScoreSet. "
            "Found type {}.".format(type(instance).__name__)
        )


@transaction.atomic
def delete_experimentset(experimentset):
    if not isinstance(experimentset, ExperimentSet):
        raise TypeError(
            "Expected ExperimentSet, found {}.".format(
                type(experimentset).__name__))
    for child in experimentset.children:
        delete_experiment(child)
    experimentset.delete()


@transaction.atomic
def delete_experiment(experiment):
    if not isinstance(experiment, Experiment):
        raise TypeError(
            "Expected Experiment, found {}.".format(
                type(experiment).__name__))
    for child in experiment.children:
        delete_scoreset(child)
    experiment.delete()


@transaction.atomic
def delete_scoreset(scoreset):
    if not isinstance(scoreset, ScoreSet):
        raise TypeError(
            "Expected ScoreSet, found {}.".format(
                type(scoreset).__name__))
    for variant in scoreset.children:
        variant.delete()
    scoreset.delete()


@transaction.atomic(savepoint=True)
def publish_dataset(dataset, user=None):
    if not dataset.private or dataset.has_public_urn:
        return dataset

    if dataset.parent:
        publish_dataset(dataset.parent, user)

    dataset.refresh_from_db()
    if isinstance(dataset, models.experimentset.ExperimentSet):
        counter = models.base.PublicDatasetCounter.objects. \
            select_for_update(nowait=False).first()
        dataset = models.experimentset.ExperimentSet.objects.filter(
            id=dataset.id
        ).select_for_update(nowait=False).first()
        dataset = models.experimentset.assign_public_urn(dataset, counter)

    elif isinstance(dataset, models.experiment.Experiment):
        dataset = models.experiment.Experiment.objects.filter(
            id=dataset.id
        ).select_for_update(nowait=False).first()
        dataset = models.experiment.assign_public_urn(dataset)

    elif isinstance(dataset, models.scoreset.ScoreSet):
        dataset = models.scoreset.ScoreSet.objects.filter(
            id=dataset.id
        ).select_for_update(nowait=False).first()
        dataset = models.scoreset.assign_public_urn(dataset)
        urns = Variant.bulk_create_urns(dataset.children.count(), dataset)
        for urn, child in zip(urns, dataset.children.all()):
            child.urn = urn
            child.save()

    else:
        raise TypeError(
            "Expected ExperimentSet, Experiment or ScoreSet. Found {}".format(
                dataset.__class__.__name__
            )
        )

    dataset.publish_date = datetime.date.today()
    dataset.private = False
    dataset.set_modified_by(user, propagate=False)
    dataset.save()
    return dataset
