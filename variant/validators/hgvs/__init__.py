"""
HGVS regex parsing for DNA, RNA and Protein specifications. `Event` refers
to a specific mutation event which does not contain any prefixes i.e.
a character from 'pcngmr' prefixing a mutation syntax like p.Leu4Gly. A
`variant` refers to an `Event` prefixed with a the former characters, which
may also be enclosed in parentheses or brackets e.g. p.(Leu5Gly)
or p.[Leu4Gly;Gly7Leu]
"""
from functools import partial

from hgvsp import multi_variant_re, single_variant_re, is_multi
from hgvsp.constants import dna_prefix, rna_prefix, protein_prefix

from django.core.exceptions import ValidationError

from core.utilities import is_null

from ...constants import wt_or_sy


def validate_multi_variant(hgvs):
    """Validate a multi variant. Raises error if None."""
    if hgvs in wt_or_sy:
        return
    match = multi_variant_re.fullmatch(hgvs)
    if not match:
        raise ValidationError(
            "'{}' is not a supported HGVS syntax.".format(hgvs)
        )


def validate_single_variant(hgvs):
    """Validate a single variant. Raises error if None."""
    if hgvs in wt_or_sy:
        return
    match = single_variant_re.fullmatch(hgvs)
    if not match:
        raise ValidationError(
            "'{}' is not a supported HGVS syntax.".format(hgvs)
        )


def validate_hgvs_string(value, level=None):
    if is_null(value):
        return
    if isinstance(value, bytes):
        value = value.decode()
    if not isinstance(value, str):
        raise ValidationError(
            "Variant HGVS values input must be strings. "
            "'{}' has the type '{}'.".format(value, type(value).__name__)
        )

    if is_multi(value):
        validate_multi_variant(value)
    else:
        validate_single_variant(value)

    if level == "nt" and value not in wt_or_sy:
        if value[0] not in dna_prefix + rna_prefix:
            raise ValidationError("{} is not a valid nucleotide syntax.")
    elif level == "p" and value not in wt_or_sy:
        if value[0] not in protein_prefix:
            raise ValidationError("{} is not a valid protein syntax.")


validate_nt_variant = partial(validate_hgvs_string, **{"level": "nt"})
validate_pro_variant = partial(validate_hgvs_string, **{"level": "p"})
