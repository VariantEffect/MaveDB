"""
Validator functions for the fields of the following classes:
    WildTypeSequence
    ReferenceGenome
    TargetGene
    Annotation
    Interval

Most validators should validate one specific field, unless fields need
to be validated against each other.
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _

DNA_SEQ_PATTERN = r'[ATGCatgc]+'


min_start_validator = MinValueValidator(
    1, message=_("The minimum starting positive is 1."))


def validate_species_name(value):
    if not value:
        raise ValidationError("Species name must not be blank.")


def validate_gene_name(value):
    if not value:
        raise ValidationError("Gene name must not be blank.")


def validate_annotation_is_not_a_second_primary(annotation, target):
    if annotation.is_primary_annotation() and target.get_primary_reference():
        raise ValidationError(
            (
                "Target already has a primary annotation relating to "
                "reference %(ref)s."
            ),
            params={'ref': target.get_primary_reference().get_short_name()}
        )

def validate_target_has_one_primary_annotation(target):
    if not target.get_primary_reference():
        raise ValidationError("A target must have one primary reference.")


def validate_interval_start_lteq_end(start, end):
    if start > end:
        raise ValidationError(
            _("An interval's start index cannot be greater than the ending index.")
        )


def validate_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_PATTERN, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )

def validate_strand(value):
    if value not in ('F', 'R'):
        raise ValidationError(
            "Interval strand must be either 'Forward' or 'Reverse'")


def validate_genome_short_name(value):
    if not value:
        raise ValidationError("Genome short name must not be blank.")


def validate_interval_is_not_a_duplicate(interval, intervals):
    for existing in intervals:
        if existing == interval:
            raise ValidationError(
                "You can not specify the same interval twice."
            )

def validate_annotation_has_unique_reference_genome(annotation, annotations):
    genomes = set([a.get_genome_name().lower() for a in annotations])
    if annotation.get_genome_name().lower() in genomes:
        raise ValidationError(
            "You can not specify multiple annotations for the same "
            "reference genome."
        )

def validate_reference_genome_has_one_external_identifier(referencegenome):
    if referencegenome.ensembl_id and referencegenome.refseq_id:
        raise ValidationError(
            "Only one external identifier can be specified for a reference"
            "genome."
        )
