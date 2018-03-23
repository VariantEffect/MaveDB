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

DNA_SEQ_PATTERN = r'[ATGCatgc]+'


def validate_target_organism(value):
    pass


def validate_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_PATTERN, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )


def validate_target_gene(value):
    pass