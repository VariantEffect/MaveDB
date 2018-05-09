from .models.experimentset import ExperimentSet
from .models.experiment import Experiment
from .models.scoreset import ScoreSet


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


def delete_experimentset(experimentset):
    if not isinstance(experimentset, ExperimentSet):
        raise TypeError(
            "Expected ExperimentSet, found {}.".format(
                type(experimentset).__name__))
    for child in experimentset.children:
        delete_experiment(child)
    experimentset.delete()


def delete_experiment(experiment):
    if not isinstance(experiment, Experiment):
        raise TypeError(
            "Expected Experiment, found {}.".format(
                type(experiment).__name__))
    for child in experiment.children:
        delete_scoreset(child)
    experiment.delete()


def delete_scoreset(scoreset):
    if not isinstance(scoreset, ScoreSet):
        raise TypeError(
            "Expected ScoreSet, found {}.".format(
                type(scoreset).__name__))
    for variant in scoreset.children:
        variant.delete()
    scoreset.delete()

