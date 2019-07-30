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
import re

from core.utilities import is_null

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _

DNA_SEQ_PATTERN = r"[ATGCatgc]+"


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
def validate_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_PATTERN, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.", params={"seq": seq}
        )


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
