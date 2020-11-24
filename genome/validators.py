"""
Validator functions for the fields of the following classes:
    WildTypeSequence
    ReferenceGenome
    TargetGene
    ReferenceMap
    GenomicInterval

Most validators should validate one specific field, unless fields need
to be validated against each other.
"""
from core.utilities import is_null

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _

from fqfa.validator.validator import (
    dna_bases_validator,
    amino_acids_validator,
)

AA_LETTERS = "ABCDEFGHIKLMNPQRSTVWXYZ"
DNA_LETTERS = "ATCG"

DNA_SEQ_PATTERN = fr"[{DNA_LETTERS}]+"
AA_SEQ_PATTERN = fr"[{AA_LETTERS}]+"


min_start_validator = MinValueValidator(
    1, message=_("Start coordinate must be a positive integer.")
)
min_end_validator = MinValueValidator(
    1, message=_("End coordinate must be a positive integer.")
)


# GenomicInterval
# ------------------------------------------------------------------------- #
def validate_interval_start_lteq_end(start, end):
    # Intervals may be underspecified, but will be ignored so skip validation.
    if start is None or end is None:
        return
    if start > end:
        raise ValidationError(
            (
                "An interval's starting coordinate cannot be greater than the "
                "ending coordinate."
            )
        )


def validate_strand(value):
    if value not in ("+", "-"):
        raise ValidationError(
            "GenomicInterval strand must be either '+' or '-'"
        )


def validate_chromosome(value):
    # Intervals may be underspecified, but will be ignored so skip validation.
    if value is None:
        return
    if is_null(value):
        raise ValidationError("Chromosome identifier must not be null.")


def validate_unique_intervals(intervals):
    for interval1 in intervals:
        for interval2 in intervals:
            if (
                (interval1.pk is not None)
                and (interval2.pk is not None)
                and (interval1.pk == interval2.pk)
            ):
                continue
            elif interval1 is interval2:
                continue
            elif interval1.equals(interval2):
                raise ValidationError(
                    "You can not specify the same interval twice."
                )


# WildTypeSequence
# ------------------------------------------------------------------------- #
def validate_wildtype_sequence(seq, as_type="any"):
    from .models import WildTypeSequence

    # Explicitly check for these cases as they are also valid AA sequences.
    if is_null(seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.", params={"seq": seq}
        )

    seq = seq.upper()
    is_dna = dna_bases_validator(seq) is not None
    is_aa = amino_acids_validator(seq) is not None

    if as_type == WildTypeSequence.SequenceType.DNA and not is_dna:
        raise ValidationError(
            "'%(seq)s' is not a valid DNA reference sequence.",
            params={"seq": seq},
        )
    elif as_type == WildTypeSequence.SequenceType.PROTEIN and not is_aa:
        raise ValidationError(
            "'%(seq)s' is not a valid protein reference sequence.",
            params={"seq": seq},
        )
    elif (as_type == "any" or WildTypeSequence.SequenceType.INFER) and not (
        is_dna or is_aa
    ):
        raise ValidationError(
            "'%(seq)s' is not a valid DNA or protein reference sequence.",
            params={"seq": seq},
        )


def sequence_is_dna(seq):
    # Explicitly check for these cases as they are also valid AA sequences.
    if is_null(seq):
        return False
    seq = seq.upper()
    return dna_bases_validator(seq) is not None


def sequence_is_protein(seq):
    # Explicitly check for these cases as they are also valid AA sequences.
    if is_null(seq):
        return False
    seq = seq.upper()
    if dna_bases_validator(seq) is not None:
        return False  # Very likely a DNA sequence if only ATG
    return amino_acids_validator(seq) is not None


# ReferenceGenome
# ------------------------------------------------------------------------- #
def validate_organism_name(value):
    if is_null(value):
        raise ValidationError("Species name must not be null.")


def validate_reference_genome_has_one_external_identifier(referencegenome):
    if not referencegenome.genome_id:
        raise ValidationError(
            "Only one external identifier can be specified for a reference"
            "genome."
        )


def validate_genome_short_name(value):
    if is_null(value):
        raise ValidationError("Genome short name must not be null.")


# ReferenceMap
# ------------------------------------------------------------------------- #
def validate_map_has_unique_reference_genome(annotations):
    genomes = set(
        [str(a.get_reference_genome_name()).lower() for a in annotations]
    )
    if len(genomes) < len(annotations):
        raise ValidationError(
            "Each reference map must specify a different reference genome."
        )


def validate_map_has_at_least_one_interval(reference_map):
    if not reference_map.get_intervals().count():
        raise ValidationError(
            "You must specify at least one interval for each reference map."
        )


def validate_at_least_one_map(reference_maps):
    if not len(reference_maps):
        raise ValidationError(
            "A target must have at least one reference map specified."
        )


def validate_one_primary_map(reference_maps):
    primary_count = sum(a.is_primary_reference_map() for a in reference_maps)
    if primary_count > 1 or primary_count < 1:
        raise ValidationError(
            ("A target must have one primary reference map.")
        )


# TargetGene
# ------------------------------------------------------------------------- #
def validate_gene_name(value):
    if is_null(value):
        raise ValidationError("Gene name must not be null.")
