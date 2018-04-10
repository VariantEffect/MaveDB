"""
Validator functions for the fields of the following classes:
    TargetOrganism
    WildTypeSequence
    ReferenceGenome
    TargetGene

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


def validate_target_organism(value):
    pass


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


def validate_target_gene(value):
    pass