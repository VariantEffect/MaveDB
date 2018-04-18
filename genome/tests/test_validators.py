from django.test import TestCase
from django.core.exceptions import ValidationError

from dataset.constants import nan_col_values
from metadata.factories import (
    EnsemblIdentifierFactory, RefseqIdentifierFactory
)

from ..factories import (
    ReferenceMapFactory,
    ReferenceGenomeFactory,
    IntervalFactory
)
from ..validators import (
    validate_interval_start_lteq_end,
    validate_wildtype_sequence,
    validate_gene_name,
    validate_genome_short_name,
    validate_interval_is_not_a_duplicate,
    validate_species_name,
    validate_strand,
    validate_annotation_has_unique_reference_genome,
    validate_reference_genome_has_one_external_identifier,
    validate_chromosome,
    validate_unique_intervals,
    validate_at_least_one_annotation,
    validate_one_primary_annotation,
    validate_annotation_has_at_least_one_interval,
)


class TestIntervalValidators(TestCase):
    """
    Tests validator functions throw the correct errors for :class:`Interval`.
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

    def test_ve_interval_already_in_intervals(self):
        interval = IntervalFactory()
        intervals = [IntervalFactory(
            start=interval.start,
            end=interval.end,
            chromosome=interval.chromosome,
            strand=interval.strand
        )]
        with self.assertRaises(ValidationError):
            validate_interval_is_not_a_duplicate(interval, intervals)

    def test_ve_duplicate_interval_chromosome_case_ignored(self):
        interval = IntervalFactory()
        intervals = [
            IntervalFactory(
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
        validate_strand('F')
        validate_strand('R')

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

    def test_ve_reference_genome_has_two_external_identifiers(self):
        ens_id = EnsemblIdentifierFactory()
        rs_id = RefseqIdentifierFactory()
        referencegenome = ReferenceGenomeFactory()
        referencegenome.ensembl_id = ens_id
        referencegenome.refseq_id = rs_id
        referencegenome.save()
        with self.assertRaises(ValidationError):
            validate_reference_genome_has_one_external_identifier(
                referencegenome)

    def test_passes_reference_genome_has_one__external_identifiers(self):
        ens_id = EnsemblIdentifierFactory()
        rs_id = RefseqIdentifierFactory()
        referencegenome = ReferenceGenomeFactory()
        referencegenome.ensembl_id = ens_id
        referencegenome.save()
        validate_reference_genome_has_one_external_identifier(referencegenome)

        referencegenome.ensembl_id = None
        referencegenome.refseq_id = rs_id
        referencegenome.save()
        validate_reference_genome_has_one_external_identifier(referencegenome)


class TestAnnotationValidators(TestCase):
    """
    Tests validators asscociated with :class:`ReferenceMap`:

        - validate_annotation_has_unique_reference_genome
        - validate_annotation_has_at_least_one_interval
        - validate_unique_intervals
    """
    def test_ve_annotation_does_not_have_a_unique_genome(self):
        annotation1 = ReferenceMapFactory()
        annotation2 = ReferenceMapFactory(
            genome=annotation1.get_reference_genome(),
            target=annotation1.get_target_gene()
        )
        with self.assertRaises(ValidationError):
            validate_annotation_has_unique_reference_genome(
                [annotation1, annotation2]
            )

    def test_ve_duplicate_intervals_in_list(self):
        interval = IntervalFactory()
        intervals = [IntervalFactory(
            start=interval.start,
            end=interval.end,
            chromosome=interval.chromosome,
            strand=interval.strand
        ), interval]
        with self.assertRaises(ValidationError):
            validate_unique_intervals(intervals)

    def test_ve_no_intervals_associated_with_annotation(self):
        annotation = ReferenceMapFactory()
        IntervalFactory(annotation=annotation)
        validate_annotation_has_at_least_one_interval(annotation)  # passes

        annotation = ReferenceMapFactory()
        with self.assertRaises(ValidationError):
            validate_annotation_has_at_least_one_interval(annotation)

    def test_ve_missing_primary_annotation(self):
        annotation = ReferenceMapFactory()
        validate_one_primary_annotation([annotation])  # passes

        annotation.set_is_primary(primary=False)
        annotation.save()
        with self.assertRaises(ValidationError):
            validate_one_primary_annotation([annotation])

    def test_ve_target_has_two_primary_annotations(self):
        annotation1 = ReferenceMapFactory()
        annotation2 = ReferenceMapFactory()
        with self.assertRaises(ValidationError):
            validate_one_primary_annotation([annotation2, annotation1])

    def test_ve_no_annotations(self):
        with self.assertRaises(ValidationError):
            validate_at_least_one_annotation([])


class TestTargetGeneValidators(TestCase):
    """
    Tests validators asscociated with :class:`TargetGene`:

        - validate_gene_name
        - validate_target_has_one_primary_annotation
    """
    def test_ve_null_gene_name(self):
        for v in nan_col_values:
            with self.assertRaises(ValidationError):
                validate_gene_name(v)
