import datetime

from django.db import transaction

from dataset import models
from variant.models import Variant
from urn.models import get_model_by_urn

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


@transaction.atomic
def publish_dataset(dataset, user=None):
    """
    Publishes a dataset by traversing the parent tree. Assigns a public
    urn of the format <urn:mavedb:X>, sets the private bit and associated
    publish metadata.
    
    Does nothing if the dataset already has a public urn or is not private.
    
    Parameters
    ----------
    dataset : `models.base.DatasetModel`
        The dataset to publish.
    user :
        The user requesting the publish.
        
    Raises
    ------
    TypeError : Not a dataset

    Returns
    -------
    `models.base.DatasetModel`
        The published dataset.
    """
    if not isinstance(dataset, models.base.DatasetModel):
        raise TypeError(
            "Expected a DatasetModel instance. Found {}".format(
                dataset.__class__.__name__
            )
        )
    
    if not dataset.private or dataset.has_public_urn:
        return dataset
    
    scoreset = None
    experiment = None
    # Full refresh on on the dataset including nested parents.
    dataset = get_model_by_urn(dataset.urn)
    
    if isinstance(dataset, models.scoreset.ScoreSet):
        experimentset = models.experimentset.assign_public_urn(
            dataset.experiment.experimentset)
        experiment = models.experiment.assign_public_urn(
            dataset.experiment)
        scoreset = models.scoreset.assign_public_urn(
            dataset)
        urns = Variant.bulk_create_urns(scoreset.children.count(), scoreset)
        for urn, child in zip(urns, scoreset.children.all()):
            child.urn = urn
            child.save()
    elif isinstance(dataset, models.experiment.Experiment):
        experimentset = models.experimentset.assign_public_urn(
            dataset.experimentset)
        experiment = models.experiment.assign_public_urn(
            dataset)
    elif isinstance(dataset, models.experimentset.ExperimentSet):
        experimentset = models.experimentset.assign_public_urn(dataset)
    else:
        raise TypeError(
            "Expected ExperimentSet, Experiment or ScoreSet. Found {}".format(
                dataset.__class__.__name__
            )
        )
    # Note: assigning a public urn to a child will alter `last_child_value`
    # of the parent. Before saving below, call `refresh_from_db` to update
    # any changes made when a child urn is assigned. Otherwise an outdated
    # version of the parent will over-write the most recent changes.
    if scoreset:
        scoreset.refresh_from_db()
        scoreset.publish_date = datetime.date.today()
        scoreset.private = False
        scoreset.set_modified_by(user, propagate=False)
        scoreset.save()
        
    if experiment:
        experiment.refresh_from_db()
        experiment.publish_date = datetime.date.today()
        experiment.private = False
        experiment.set_modified_by(user, propagate=False)
        experiment.save()
        
    if experimentset:
        experimentset.refresh_from_db()
        experimentset.publish_date = datetime.date.today()
        experimentset.private = False
        experimentset.set_modified_by(user, propagate=False)
        experimentset.save()

    dataset.refresh_from_db()
    return get_model_by_urn(dataset.urn) # Full refresh on nested parents.
