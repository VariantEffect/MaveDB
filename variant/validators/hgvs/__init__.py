"""
HGVS regex parsing for DNA, RNA and Protein specifications. `Event` refers
to a specific mutation event which does not contain any prefixes i.e.
a character from 'pcngmr' prefixing a mutation syntax like p.Leu4Gly. A
`variant` refers to an `Event` prefixed with a the former characters, which
may also be enclosed in parentheses or brackets e.g. p.(Leu5Gly)
or p.[Leu4Gly;Gly7Leu]
"""
from functools import partial

from django.core.exceptions import ValidationError
from hgvsp import is_multi, protein, dna, infer_level, Level
from hgvsp.constants import (
    protein_prefix,
    genomic_prefix,
    non_coding_prefix,
    coding_prefix,
)

from core.utilities import is_null
from ...constants import wt_or_sy


def validate_multi_variant(hgvs):
    """Validate a multi variant. Raises error if None."""
    if hgvs in wt_or_sy:
        return

    if infer_level(hgvs) == Level.PROTEIN:
        match = protein.multi_variant_re.fullmatch(hgvs)
    elif infer_level(hgvs) == Level.DNA:
        match = dna.multi_variant_re.fullmatch(hgvs)
    else:
        match = None

    if not match:
        raise ValidationError(f"'{hgvs}' is not supported HGVS syntax.")


def validate_single_variant(hgvs):
    """Validate a single variant. Raises error if None."""
    if hgvs in wt_or_sy:
        return

    if infer_level(hgvs) == Level.PROTEIN:
        match = protein.single_variant_re.fullmatch(hgvs)
    elif infer_level(hgvs) == Level.DNA:
        match = dna.single_variant_re.fullmatch(hgvs)
    else:
        match = None

    if not match:
        raise ValidationError(f"'{hgvs}' is not supported HGVS syntax.")


def validate_hgvs_string(value, column=None, tx_present=False):
    if is_null(value):
        return
    if isinstance(value, bytes):
        value = value.decode()
    if not isinstance(value, str):
        raise ValidationError(
            "Variant HGVS values input must be strings. "
            "'{}' has the type '{}'.".format(value, type(value).__name__)
        )

    if value in wt_or_sy:
        return

    if is_multi(value):
        validate_multi_variant(value)
    else:
        validate_single_variant(value)

    if column == "nt":
        if tx_present:
            if value[0] not in genomic_prefix:
                raise ValidationError(
                    f"'{value}' is not a genomic variant (prefix 'g.'). "
                    f"Nucletotide variants must be genomic if transcript "
                    f"variants are also defined."
                )
        else:
            if value[0] not in coding_prefix + non_coding_prefix:
                raise ValidationError(
                    f"'{value}' is not a transcript variant. The accepted "
                    f"transcript variant prefixes are 'c.', 'n.'."
                )
    elif column == "tx":
        if value[0] not in coding_prefix + non_coding_prefix:
            raise ValidationError(
                f"'{value}' is not a transcript variant. The accepted "
                f"transcript variant prefixes are 'c.', 'n.'."
            )
    elif column == "p":
        if value[0] not in protein_prefix:
            raise ValidationError(
                f"'{value}' is not a protein variant. The accepted "
                f"protein variant prefix is 'p.'."
            )
    else:
        raise ValueError(
            "Unknown column '{}'. Expected nt, tx or p".format(column)
        )


validate_nt_variant = partial(validate_hgvs_string, **{"column": "nt"})
validate_tx_variant = partial(validate_hgvs_string, **{"column": "tx"})
validate_pro_variant = partial(validate_hgvs_string, **{"column": "p"})
