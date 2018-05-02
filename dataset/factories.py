"""
dataset.factories
=================

This module contains factory methods for creating test fixtures. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import factory.faker
from factory.django import DjangoModelFactory

from metadata.factories import (
    KeywordFactory, SraIdentifierFactory, DoiIdentifierFactory,
    PubmedIdentifierFactory
)

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

    method_text = factory.faker.Faker('text', max_nb_chars=1500)
    abstract_text = factory.faker.Faker('text', max_nb_chars=1500)
    title = factory.faker.Faker('text', max_nb_chars=250)
    short_description = factory.faker.Faker('text', max_nb_chars=1000)
    extra_metadata = {"foo": "bar"}
    private = True

    @factory.post_generation
    def keywords(self, create, extracted, **kwargs):
        if create:
            kw = KeywordFactory()
            self.add_keyword(kw)

    @factory.post_generation
    def sra_ids(self, create, extracted, **kwargs):
        if create:
            id_ = SraIdentifierFactory()
            self.add_identifier(id_)

    @factory.post_generation
    def doi_ids(self, create, extracted, **kwargs):
        if create:
            id_ = DoiIdentifierFactory()
            self.add_identifier(id_)

    @factory.post_generation
    def pubmed_ids(self, create, extracted, **kwargs):
        if create:
            id_ = PubmedIdentifierFactory()
            self.add_identifier(id_)


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


class ExperimentWithScoresetFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`Experiment` with an
    associated fully specified :class:`ScoreSet` (target, references etc).
    """
    class Meta:
        model = Experiment

    experimentset = factory.SubFactory(ExperimentSetFactory)

    @factory.post_generation
    def scoreset(self, create, extracted, **kwargs):
        if create:
            ScoreSetWithTargetFactory(experiment=self, private=self.private)


class ScoreSetFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`Scoreset`.
    """
    class Meta:
        model = ScoreSet

    experiment = factory.SubFactory(ExperimentFactory)
    dataset_columns = default_dataset()


class ScoreSetWithTargetFactory(DatasetModelFactory):
    """
    Factory for producing test instances for :class:`Scoreset` with an
    associated fully specified :class:`TargetGene` (references etc).
    """
    class Meta:
        model = ScoreSet

    experiment = factory.SubFactory(ExperimentFactory)
    dataset_columns = default_dataset()

    @factory.post_generation
    def target(self, create, extracted, **kwargs):
        from genome.factories import TargetGeneWithReferenceMapFactory
        if create and not self.get_target():
            TargetGeneWithReferenceMapFactory(scoreset=self)
