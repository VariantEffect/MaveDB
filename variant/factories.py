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
from dataset.factories import ScoreSetFactory
from dataset.models.scoreset import default_dataset
from .models import Variant


def make_data():
    """Creates the variant score/count data json object"""
    return {
        constants.variant_score_data: {
            default_dataset()[constants.score_columns][
                0
            ]: factory.fuzzy.FuzzyFloat(low=-1, high=1).fuzz()
        },
        constants.variant_count_data: {},
    }


def generate_hgvs(prefix="c"):
    """Generates a random hgvs string from a small sample."""
    if prefix == "p":
        return choice(
            [
                "p.Ala4Leu",
                "p.G78L",
                "p.(Ala32*)",
                "p.C28_L29delinsTGL",
                "p.(Ala32_Leu33ins(5))",
            ]
        )
    else:
        alt = choice("ATCG")
        ref = choice("ATCG")
        return f"{prefix}.{choice(range(1, 100))}{ref}>{alt}"


class VariantFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`Variant`.
    """

    class Meta:
        model = Variant

    urn = None
    scoreset = factory.SubFactory(ScoreSetFactory)
    hgvs_nt = factory.LazyFunction(lambda: generate_hgvs("g"))
    hgvs_pro = factory.LazyFunction(lambda: generate_hgvs("p"))
    hgvs_tx = factory.LazyFunction(lambda: generate_hgvs("c"))
    data = factory.LazyFunction(make_data)
