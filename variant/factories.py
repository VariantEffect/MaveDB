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
from dataset.models.scoreset import default_dataset
from dataset.factories import ScoreSetFactory

from .models import Variant


dna_to_rna = "ATCGXN".maketrans(
    {"A": "a", "T": "u", "G": "g", "C": "c", "X": "x", "N": "n", "H": "h"}
)
dna_hgvs = ["c.101G>C", "c.10C>A", "c.41G>A", "c.53G>T", "c.17C>G"]
rna_hgvs = [x.replace("c", "r").translate(dna_to_rna) for x in dna_hgvs]
protein_hgvs = [
    "p.Ala4Leu",
    "p.G78L",
    "p.(Ala32*)",
    "p.C28_L29delinsTGL",
    "p.(Ala32_Leu33ins(5))",
]


# Instance is passed in by default by factory_boy
def make_data(instance=None):
    return {
        constants.variant_score_data: {
            default_dataset()[constants.score_columns][
                0
            ]: factory.fuzzy.FuzzyFloat(low=-1, high=1).fuzz()
        },
        constants.variant_count_data: {},
    }


def generate_hgvs(prefix="c", comma_in_rna=False):
    """Generates a random hgvs string from a small sample."""
    if prefix == "r":
        if comma_in_rna:
            return "r.[897u>g,832_960del]"
        return choice(rna_hgvs)
    elif prefix == "p":
        return choice(protein_hgvs)
    else:
        return choice(dna_hgvs)


class VariantFactory(DjangoModelFactory):
    """
    Factory for producing test instances for :class:`Variant`.
    """

    class Meta:
        model = Variant

    urn = None
    scoreset = factory.SubFactory(ScoreSetFactory)
    hgvs_nt = factory.fuzzy.FuzzyChoice(dna_hgvs)
    hgvs_pro = factory.fuzzy.FuzzyChoice(protein_hgvs)
    data = factory.lazy_attribute(make_data)
