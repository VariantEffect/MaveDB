"""
variant.factories
=================

This module contains factory methods for creating test fixtures. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""
from random import choice

import factory
import factory.fuzzy
from factory.django import DjangoModelFactory

import dataset.constants as constants
from dataset.models.scoreset import ScoreSet, default_dataset
from dataset.factories import ScoreSetFactory

from .models import Variant


sample_hgvs = ['c.101G>C', 'c.10C>A', 'c.41G>A', 'c.53G>T', 'c.17C>G']


def make_data(instance):
    return {
        constants.variant_score_data: {
            default_dataset()[constants.score_columns][0]:
                factory.fuzzy.FuzzyFloat(low=-1, high=1).fuzz()
        },
        constants.variant_count_data: {},
    }


def generate_hgvs():
    """Generates a random hgvs string from a small sample."""
    return choice(sample_hgvs)


class VariantFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`Variant`.
    """
    class Meta:
        model = Variant

    urn = None
    scoreset = factory.SubFactory(ScoreSetFactory)
    hgvs = factory.fuzzy.FuzzyChoice(sample_hgvs)
    data = factory.lazy_attribute(make_data)
