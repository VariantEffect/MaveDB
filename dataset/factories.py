"""
dataset.factories
=================

This module contains factory methods for creating test fixtures. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import factory.fuzzy
from factory.django import DjangoModelFactory

from .models.base import DatasetModel
from .models.experimentset import ExperimentSet
from .models.experiment import Experiment
from .models.scoreset import ScoreSet, default_dataset


class DatasetModelFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`DatasetModel`.
    """
    class Meta:
        model = DatasetModel

    method_text = factory.fuzzy.FuzzyText(length=500)
    abstract_text = factory.fuzzy.FuzzyText(length=500)
    title = factory.fuzzy.FuzzyText(length=64)
    short_description = factory.fuzzy.FuzzyText(length=256)
    private = True


class ExperimentSetFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`ExperimentSet`.
    """
    class Meta:
        model = ExperimentSet


class ExperimentFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`Experiment`.
    """
    class Meta:
        model = Experiment

    experimentset = factory.SubFactory(ExperimentSetFactory)


class ScoreSetFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`Scoreset`.
    """
    class Meta:
        model = ScoreSet

    experiment = factory.SubFactory(ExperimentFactory)
    dataset_columns = default_dataset()

    @factory.post_generation
    def target(self, create, extracted, **kwargs):
        from genome.factories import (
            IntervalFactory, AnnotationFactory, TargetGeneFactory
        )

        if not create:
             return

        if extracted:
            extracted.scoreset = self
            extracted.save()
        elif 'target' in kwargs:
            kwargs['target'].scoreset = self
            kwargs['target'].save()
        else:
            target = TargetGeneFactory(scoreset=None)
            annotation = AnnotationFactory(target=target)
            annotation.save()

            interval = IntervalFactory(annotation=annotation)
            interval.save()

            target.scoreset = self
            target.scoreset.save()
