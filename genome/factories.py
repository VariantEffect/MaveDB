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

from .models import (
    TargetGene,
    WildTypeSequence,
    Annotation,
    ReferenceGenome,
    Interval
)


strand_choices = (
    Interval.STRAND_CHOICES[0][0], Interval.STRAND_CHOICES[1][0]
)
chr_chars = string.digits[1:] + 'XY'


class WildTypeSequenceFactory(DjangoModelFactory):
    """
    Creates a :class:`WildTypeSequence` instance with a randomly generated
    sequence of nucleotides.
    """
    class Meta:
        model = WildTypeSequence

    sequence = factory.fuzzy.FuzzyText(length=50, chars='ATCG')


class IntervalFactory(DjangoModelFactory):
    """
    Creates an :class:`Interval` with randomly generated start, stop, chr
    and strand.
    """
    class Meta:
        model = Interval

    start = 1
    end = factory.fuzzy.FuzzyInteger(low=1)
    chromosome = factory.fuzzy.FuzzyText(prefix='chr', length=1, chars=chr_chars)
    strand = factory.fuzzy.FuzzyChoice(choices=strand_choices)


class ReferenceGenomeFactory(DjangoModelFactory):
    """
    Creates a primary :class:`ReferenceGenome` instance with random
    choice selection for the attributes `short_name` and `species_name`.
    """
    class Meta:
        model = ReferenceGenome

    short_name = factory.fuzzy.FuzzyChoice(['hg38'])
    species_name = factory.fuzzy.FuzzyChoice(['Homo spaiens'])
    is_primary = True


class AnnotationFactory(DjangoModelFactory):
    """
    Creates an :class:`Annotation` instance with a :class:`ReferenceGenome`
    relation and a set of 3 randomly generated :class:`Interval`
    instnaces.
    """
    class Meta:
        model = Annotation

    genome = factory.SubFactory(ReferenceGenomeFactory)

    @factory.post_generation
    def intervals(self, create, extracted, **kwargs):
        if not create:
            # No instance created so do nothing.
            return
        elif not extracted:
            # No intervals were passed in, created 3 random ones.
            for i in range(3):
                self.intervals.add(IntervalFactory())
        elif extracted:
            # A list of intervals were passed in, add them.
            for interval in extracted:
                self.intervals.add(interval)


class TargetGeneFactory(DjangoModelFactory):
    """
    Factory for creating simple minimally instantiated :class:`TargetGene`
    instances.
    """
    class Meta:
        model = TargetGene

    name = factory.fuzzy.FuzzyChoice(['BRCA1', 'JAK', 'STAT', 'MAPK'])
    wt_sequence = factory.SubFactory(WildTypeSequenceFactory)

    @factory.post_generation
    def annotations(self, create, extracted, **kwargs):
        if not create:
            # No instance created so do nothing.
            return
        elif not extracted:
            # No annotations were passed in, created 3 random ones.
            for i in range(3):
                self.annotations.add(AnnotationFactory())
        elif extracted:
            # A list of annotations were passed in, add them.
            for annotation in extracted:
                self.annotations.add(annotation)
