"""
genome.factories
=================

This module contains factory methods for creating test fixtures. If there are
any updates to the models which will have an impact on the tests, then they
can be changed once here instead of throughout all the tests. This will help
with future maintainability.
"""

import string
import factory.fuzzy
from factory.django import DjangoModelFactory

from dataset.factories import ScoreSetFactory
from metadata.factories import (
    GenomeIdentifierFactory,
    UniprotIdentifierFactory,
    RefseqIdentifierFactory,
    EnsemblIdentifierFactory,
)

from .models import (
    TargetGene,
    WildTypeSequence,
    ReferenceMap,
    ReferenceGenome,
    GenomicInterval,
)

strand_choices = (
    GenomicInterval.STRAND_CHOICES[0][0],
    GenomicInterval.STRAND_CHOICES[1][0],
)
chr_chars = string.digits[1:] + "XY"


class WildTypeSequenceFactory(DjangoModelFactory):
    """
    Creates a :class:`WildTypeSequence` instance with a randomly generated
    sequence of nucleotides.
    """

    class Meta:
        model = WildTypeSequence

    sequence = factory.fuzzy.FuzzyText(length=30, chars="ATCG")
    sequence_type = WildTypeSequence.SequenceType.INFER


class ReferenceGenomeFactory(DjangoModelFactory):
    """
    Creates a primary :class:`ReferenceGenome` instance with random
    choice selection for the attributes `short_name` and `organism_name`.
    """

    class Meta:
        model = ReferenceGenome
        # django_get_or_create = ("short_name",)

    short_name = factory.fuzzy.FuzzyChoice(["hg38", "hg37", "hg36"])
    organism_name = factory.fuzzy.FuzzyChoice(["Homo sapiens"])
    genome_id = factory.SubFactory(GenomeIdentifierFactory)


class TargetGeneFactory(DjangoModelFactory):
    """
    Factory for creating simple minimally instantiated :class:`TargetGene`
    instances.
    """

    class Meta:
        model = TargetGene

    scoreset = factory.SubFactory(ScoreSetFactory)
    name = factory.fuzzy.FuzzyChoice(["BRCA1", "JAK", "STAT", "MAPK", "EGF"])
    wt_sequence = factory.SubFactory(WildTypeSequenceFactory)
    ensembl_id = factory.SubFactory(EnsemblIdentifierFactory)
    refseq_id = factory.SubFactory(RefseqIdentifierFactory)
    uniprot_id = factory.SubFactory(UniprotIdentifierFactory)


class TargetGeneWithReferenceMapFactory(TargetGeneFactory):
    @factory.post_generation
    def target(self, create, extracted, **kwargs):
        if create:
            ReferenceMapWithIntervalsFactory(target=self)


class ReferenceMapFactory(DjangoModelFactory):
    """
    Creates an :class:`ReferenceMap` instance with a :class:`ReferenceGenome`
    relation and a set of 3 randomly generated :class:`GenomicInterval`
    instances.
    """

    class Meta:
        model = ReferenceMap

    genome = factory.SubFactory(ReferenceGenomeFactory)
    target = factory.SubFactory(TargetGeneFactory)
    is_primary = True


class ReferenceMapWithIntervalsFactory(ReferenceMapFactory):
    @factory.post_generation
    def intervals(self, create, extracted, **kwargs):
        if create:
            for i in range(3):
                GenomicIntervalFactory(reference_map=self)


class GenomicIntervalFactory(DjangoModelFactory):
    """
    Creates an :class:`GenomicInterval` with randomly generated `start`,
    `stop`, `chromosome` and `strand`.
    """

    class Meta:
        model = GenomicInterval

    start = 1
    end = factory.fuzzy.FuzzyInteger(low=1, high=1000)
    chromosome = factory.fuzzy.FuzzyText(
        prefix="chr", length=1, chars=chr_chars
    )
    strand = factory.fuzzy.FuzzyChoice(choices=strand_choices)
    reference_map = factory.SubFactory(ReferenceMapFactory)
