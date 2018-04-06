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

from main.models import Licence

from dataset.constants import (
    score_columns, count_columns, metadata_columns,
    hgvs_column, required_score_column
)
from dataset.models.base import DatasetModel
from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet, default_dataset


class DatasetModelFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`DatasetModel`.
    """
    class Meta:
        model = DatasetModel

    method_text = factory.fuzzy.FuzzyText(length=100)
    abstract_text = factory.fuzzy.FuzzyText(length=100)


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

    target = 'BRCA1'
    wt_sequence = factory.fuzzy.FuzzyText(length=50, chars='ATCG')
    experimentset = factory.SubFactory(ExperimentSetFactory)


class ScoreSetFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`Scoreset`.
    """
    class Meta:
        model = ScoreSet

    experiment = factory.SubFactory(ExperimentFactory)
    dataset_columns = default_dataset()


