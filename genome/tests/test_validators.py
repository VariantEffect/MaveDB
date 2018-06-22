from django.test import TestCase
from django.core.exceptions import ValidationError

from dataset.constants import nan_col_values
from metadata.factories import (
    EnsemblIdentifierFactory, RefseqIdentifierFactory
)

from ..factories import (
    ReferenceMapFactory,
    ReferenceGenomeFactory,
    GenomicIntervalFactory
)
from ..validators import (
    validate_interval_start_lteq_end,
    validate_wildtype_sequence,
    validate_gene_name,
    validate_genome_short_name,
    validate_species_name,
    validate_strand,
    validate_map_has_unique_reference_genome,
    validate_reference_genome_has_one_external_identifier,
    validate_chromosome,
    validate_unique_intervals,
    validate_at_least_one_map,
    validate_one_primary_map,
    validate_map_has_at_least_one_interval,
)


class TestIntervalValidators(TestCase):
    """
    Tests validator functions throw the correct errors for :class:`GenomicInterval`.
    've' is short for 'ValidationError'. Tests:

        - validate_interval_start_lteq_end
        - validate_interval_is_not_a_duplicate
        - validate_strand
        - validate_chromosome
    """
    def test_ve_when_start_is_greater_than_end(self):
        with self.assertRaises(ValidationError):
            validate_interval_start_lteq_end(start=3, end=2)

    def test_pass_when_start_equal_end(self):
        validate_interval_start_lteq_end(start=1, end=1)

    def test_ve_duplicate_interval_chromosome_case_ignored(self):
        interval = GenomicIntervalFactory()
        intervals = [
            GenomicIntervalFactory(
                start=interval.start,
                end=interval.end,
                chromosome=interval.chromosome.upper(),
                strand=interval.strand
            ),
            interval
        ]
        with self.assertRaises(ValidationError):
            validate_unique_intervals(intervals)

    def test_ve_strand_not_in_choices(self):
        with self.assertRaises(ValidationError):
            validate_strand('f')

        with self.assertRaises(ValidationError):
            validate_strand('r')

        with self.assertRaises(ValidationError):
            validate_strand('Forward')

        with self.assertRaises(ValidationError):
            validate_strand('Reverse')

        # Should pass
        validate_strand('+')
        validate_strand('-')

    def test_ve_null_chr(self):
        for v in nan_col_values:
            with self.assertRaises(ValidationError):
                validate_chromosome(v)


class TestWildTypeSequenceValidators(TestCase):
    """
    Tests validators asscociated with :class:`WildTypeSequence`. Tests:

        - validate_wildtype_sequence
    """
    def test_ve_not_a_sequence_of_nucleotides(self):
        with self.assertRaises(ValidationError):
            validate_wildtype_sequence('AAF')

    def test_ve_null(self):
        for v in nan_col_values:
            with self.assertRaises(ValidationError):
                validate_wildtype_sequence(v)

    def test_passes_lowercase_nucleotides(self):
        validate_wildtype_sequence('atcg')

    def test_passes_uppercase_nucleotides(self):
        validate_wildtype_sequence('ATCG')


class TestReferenceGenomeValidators(TestCase):
    """
    Tests validators asscociated with :class:`ReferenceGenome`:

        - validate_reference_genome_has_one_external_identifier
        - validate_species_name
        - validate_genome_short_name
    """
    def test_ve_null_species_name(self):
        for v in nan_col_values:
            with self.assertRaises(ValidationError):
                validate_species_name(v)

    def test_ve_null_genome_short_name(self):
        for v in nan_col_values:
            with self.assertRaises(ValidationError):
                validate_genome_short_name(v)

    def test_ve_reference_genome_has_no_external_identifiers(self):
        referencegenome = ReferenceGenomeFactory(genome_id=None)
        with self.assertRaises(ValidationError):
            validate_reference_genome_has_one_external_identifier(
                referencegenome)

    def test_passes_reference_genome_has_one_external_identifiers(self):
        referencegenome = ReferenceGenomeFactory()
        validate_reference_genome_has_one_external_identifier(referencegenome)


class TestReferenceMapValidators(TestCase):
    """
    Tests validators asscociated with :class:`ReferenceMap`:

        - validate_map_has_unique_reference_genome
        - validate_map_has_at_least_one_interval
        - validate_unique_intervals
    """
    def test_ve_reference_map_does_not_have_a_unique_genome(self):
        reference_map1 = ReferenceMapFactory()
        reference_map2 = ReferenceMapFactory(
            genome=reference_map1.get_reference_genome(),
            target=reference_map1.get_target()
        )
        with self.assertRaises(ValidationError):
            validate_map_has_unique_reference_genome(
                [reference_map1, reference_map2]
            )

    def test_ve_duplicate_intervals_in_list(self):
        interval = GenomicIntervalFactory()
        intervals = [GenomicIntervalFactory(
            start=interval.start,
            end=interval.end,
            chromosome=interval.chromosome,
            strand=interval.strand
        ), interval]
        with self.assertRaises(ValidationError):
            validate_unique_intervals(intervals)

    def test_ve_no_intervals_associated_with_reference_map(self):
        reference_map = ReferenceMapFactory()
        GenomicIntervalFactory(reference_map=reference_map)
        validate_map_has_at_least_one_interval(reference_map)  # passes

        reference_map = ReferenceMapFactory()
        with self.assertRaises(ValidationError):
            validate_map_has_at_least_one_interval(reference_map)

    def test_ve_missing_primary_maps(self):
        reference_map = ReferenceMapFactory()
        validate_one_primary_map([reference_map])  # passes

        reference_map.set_is_primary(primary=False)
        reference_map.save()
        with self.assertRaises(ValidationError):
            validate_one_primary_map([reference_map])

    def test_ve_target_has_two_primary_reference_maps(self):
        reference_map1 = ReferenceMapFactory()
        reference_map2 = ReferenceMapFactory()
        with self.assertRaises(ValidationError):
            validate_one_primary_map([reference_map2, reference_map1])

    def test_ve_no_reference_maps(self):
        with self.assertRaises(ValidationError):
            validate_at_least_one_map([])


class TestTargetGeneValidators(TestCase):
    """
    Tests validators asscociated with :class:`TargetGene`:

        - validate_gene_name
        - validate_target_has_one_primary_reference_map
    """
    def test_ve_null_gene_name(self):
        for v in nan_col_values:
            with self.assertRaises(ValidationError):
                validate_gene_name(v)
