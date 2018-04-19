"""
Validator functions for the fields of the following classes:
    WildTypeSequence
    ReferenceGenome
    TargetGene
    ReferenceMap
    Interval

Most validators should validate one specific field, unless fields need
to be validated against each other.
"""
import re

from core.utilities import is_null

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _

DNA_SEQ_PATTERN = r'[ATGCatgc]+'


min_start_validator = MinValueValidator(
    1, message=_("The minimum starting positive is 1."))
min_end_validator = MinValueValidator(
    1, message=_("The minimum starting positive is 1."))


# Interval
# ------------------------------------------------------------------------- #
def validate_interval_start_lteq_end(start, end):
    if start > end:
        raise ValidationError(
            (
                "An interval's start index cannot be greater than the ending "
                "index."
            )
        )


def validate_interval_is_not_a_duplicate(interval, intervals):
    for existing in intervals:
        if existing is interval:
            continue
        elif existing.equals(interval):
            raise ValidationError(
                "You can not specify the same interval twice."
            )


def validate_strand(value):
    if value not in ('+', '-'):
        raise ValidationError(
            "Interval strand must be either 'Forward' or 'Reverse'")


def validate_chromosome(value):
    if is_null(value):
        raise ValidationError(
            "Chromosome identifier must not be null.")


def validate_unique_intervals(intervals):
    for interval1 in intervals:
        for interval2 in intervals:
            if interval1 is interval2:
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
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )


# ReferenceGenome
# ------------------------------------------------------------------------- #
def validate_species_name(value):
    if is_null(value):
        raise ValidationError("Species name must not be null.")


def validate_reference_genome_has_one_external_identifier(referencegenome):
    if referencegenome.ensembl_id and referencegenome.refseq_id:
        raise ValidationError(
            "Only one external identifier can be specified for a reference"
            "genome."
        )


def validate_genome_short_name(value):
    if is_null(value):
        raise ValidationError("Genome short name must not be null.")


# ReferenceMap
# ------------------------------------------------------------------------- #
def validate_annotation_has_unique_reference_genome(annotations):
    genomes = set([str(a.get_reference_genome_name()).lower() for a in annotations])
    if len(genomes) < len(annotations):
        raise ValidationError(
            "Each target reference_map must be for a different reference genome."
        )


def validate_annotation_has_at_least_one_interval(annotation):
    if not annotation.get_intervals().count():
        raise ValidationError(
            "You must specify at least one interval for each reference "
            "reference_map."
        )


def validate_at_least_one_annotation(annotations):
    if not annotations:
        raise ValidationError(
            "A target must have at least one reference reference_map."
        )


def validate_one_primary_annotation(annotations):
    primary_count = sum(a.is_primary_annotation() for a in annotations)
    if primary_count > 1 or primary_count < 1:
        raise ValidationError(
            (
                "A target must have one primary reference reference_map."
            )
        )


# TargetGene
# ------------------------------------------------------------------------- #
def validate_gene_name(value):
    if is_null(value):
        raise ValidationError("Gene name must not be null.")
