"""
dataset.factories
=================

This module contains factory methods for creating test fixtures for
:class:`keyword` and subclasses of :class:`ExternalIdentifier`. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import factory.fuzzy
import factory.faker
from factory.django import DjangoModelFactory

from .models import (
    Keyword,
    SraIdentifier,
    DoiIdentifier,
    PubmedIdentifier,
    UniprotIdentifier,
    EnsemblIdentifier,
    RefseqIdentifier,
    UniprotOffset,
    RefseqOffset,
    EnsemblOffset,
    AnnotationOffset,
    GenomeIdentifier,
    ExternalIdentifier,
)


class KeywordFactory(DjangoModelFactory):
    """Factory creating a keyword with a random `text` attribute."""

    class Meta:
        model = Keyword
        django_get_or_create = ("text",)

    text = factory.faker.Faker("word")


class ExternalIdentifierFactory(DjangoModelFactory):
    """
    Factory creating :class:`SraIdentifier` instances matching the
    SRA_RUN_PATTERN
    """

    class Meta:
        model = ExternalIdentifier
        django_get_or_create = ("identifier",)


class SraIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`SraIdentifier` instances matching the
    SRA_RUN_PATTERN
    """

    class Meta:
        model = SraIdentifier
        django_get_or_create = ("identifier",)

    identifier = factory.fuzzy.FuzzyChoice(
        ["SRX3407687", "SRX3407686", "SRX366265", "PRJNA419207", "PRJNA362734"]
    )


class DoiIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`DoiIdentifier` instances with a random choice
    of doi ids.
    """

    class Meta:
        model = DoiIdentifier
        django_get_or_create = ("identifier",)

    identifier = factory.fuzzy.FuzzyChoice(
        [
            "10.1016/j.cels.2018.01.015",
            "10.1016/j.jmb.2018.02.009",
            "10.1038/s41598-017-17081-y.",
            "10.1007/978-1-4939-7366-8_6",
            "10.1073/pnas.1614437114",
        ]
    )


class PubmedIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`PubmedIdentifier` instances with a random choice
    of ids.
    """

    class Meta:
        model = PubmedIdentifier
        django_get_or_create = ("identifier",)

    reference_html = factory.fuzzy.FuzzyChoice(
        [
            "Rubin AF, <i>et al</i>. A statistical framework for analyzing deep "
            "mutational scanning data. <i>Genome Biol</i>. 2017; "
            "<b>18</b>:150.",
            "Weile J, <i>et al</i>. A framework for exhaustively mapping "
            "functional missense variants. <i>Mol. Syst. Biol</i>. 2017; "
            "<b>13</b>:957.",
            "Fowler DM and Fields S. Deep mutational scanning: a new style of "
            "protein science. <i>Nat. Methods</i>. 2014; <b>11</b>:801-7.",
            "Fowler DM, <i>et al</i>. High-resolution mapping of protein "
            "sequence-function relationships. <i>Nat. Methods</i>. 2010; "
            "<b>7</b>:741-6.",
            "Fowler DM, <i>et al</i>. Enrich: software for analysis of protein "
            "function by enrichment and depletion of variants. "
            "<i>Bioinformatics</i>. 2011; <b>27</b>:3430-1.",
        ]
    )
    identifier = factory.fuzzy.FuzzyChoice(
        ["25075907", "20711194", "29269382", "28784151", "22006916"]
    )


class UniprotIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`UniprotIdentifier` instances with a random
    identifier choice.
    """

    class Meta:
        model = UniprotIdentifier
        django_get_or_create = ("identifier",)

    identifier = factory.fuzzy.FuzzyChoice(
        ["P00533", "P01133", "P19174", "P30530", "Q7L2J0", "Q8N163"]
    )


class RefseqIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`RefseqIdentifier` instances with a random
    identifier choice.
    """

    class Meta:
        model = RefseqIdentifier
        django_get_or_create = ("identifier",)

    identifier = factory.fuzzy.FuzzyChoice(
        [
            "WP_107309473.1",
            "NP_001349131.1",
            "NR_155436.1",
            "NR_155453.1",
            "NR_155470.1",
            "YP_009472129.1",
        ]
    )


class EnsemblIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`EnsemblIdentifier` instances with a random
    identifier choice.
    """

    class Meta:
        model = EnsemblIdentifier
        django_get_or_create = ("identifier",)

    identifier = factory.fuzzy.FuzzyChoice(
        [
            "ENSG00000010404",
            "ENSG00000267816",
            "ENSG00000143384",
            "ENSG00000198001",
            "ENSG00000006062",
            "ENSG00000172936",
        ]
    )


class GenomeIdentifierFactory(ExternalIdentifierFactory):
    """
    Factory creating :class:`GenomeIdentifier` instances with a random
    identifier choice.
    """

    class Meta:
        model = GenomeIdentifier
        django_get_or_create = ("identifier",)

    identifier = factory.fuzzy.FuzzyChoice(
        [
            "GCF_000146045.2",
            "GCF_000001405.26",
            "GCF_000001405.13",
            "GCF_000146795.2",
            "GCF_000001405.11",
            "GCF_000001405.10",
        ]
    )


# AnnotationOffsets
# --------------------------------------------------------------------------- #
class AnnotationOffsetFactory(DjangoModelFactory):
    """
    Factory creating :class:`AnnotationOffset` instances with a random
    identifier accession, target and offset.
    """

    class Meta:
        model = AnnotationOffset

    offset = factory.fuzzy.FuzzyInteger(1000)


class UniprotOffsetFactory(AnnotationOffsetFactory):
    """
    Factory creating :class:`UniprotOffset` instances with a random
    identifier accession, target and offset.
    """

    class Meta:
        model = UniprotOffset

    identifier = factory.SubFactory(UniprotIdentifierFactory)
    target = factory.SubFactory(
        factory="genome.factories.TargetGeneFactory",
        uniprot_id=factory.SelfAttribute("..identifier"),
    )


class RefseqOffsetFactory(AnnotationOffsetFactory):
    """
    Factory creating :class:`RefseqOffset` instances with a random
    identifier accession, target and offset.
    """

    class Meta:
        model = RefseqOffset

    identifier = factory.SubFactory(RefseqIdentifierFactory)
    target = factory.SubFactory(
        factory="genome.factories.TargetGeneFactory",
        refseq_id=factory.SelfAttribute("..identifier"),
    )


class EnsemblOffsetFactory(AnnotationOffsetFactory):
    """
    Factory creating :class:`EnsemblOffset` instances with a random
    identifier accession, target and offset.
    """

    class Meta:
        model = EnsemblOffset

    identifier = factory.SubFactory(EnsemblIdentifierFactory)
    target = factory.SubFactory(
        factory="genome.factories.TargetGeneFactory",
        ensembl_id=factory.SelfAttribute("..identifier"),
    )
