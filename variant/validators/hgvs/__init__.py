"""
HGVS regex parsing for DNA, RNA and Protein specifications. `Event` refers
to a specific mutation event which does not contain any prefixes i.e.
a character from 'pcngmr' prefixing a mutation syntax like p.Leu4Gly. A
`variant` refers to an `Event` prefixed with a the former characters, which
may also be enclosed in parentheses or brackets e.g. p.(Leu5Gly)
or p.[Leu4Gly;Gly7Leu]
"""

from hgvsp import multi_variant_re, single_variant_re
from hgvsp import Level, Event, infer_type, infer_level
from hgvsp.rna import semi_colon_separated_re, comma_separated_re

from django.core.exceptions import ValidationError

from . import dna, rna, protein

from variant import constants

validate_event_functions = {
    Level.DNA: {
        Event.INSERTION: dna.validate_insertion,
        Event.DELETION: dna.validate_deletion,
        Event.DELINS: dna.validate_delins,
        Event.SUBSTITUTION: dna.validate_substitution,
    },
    Level.RNA: {
        Event.INSERTION: rna.validate_insertion,
        Event.DELETION: rna.validate_deletion,
        Event.DELINS: rna.validate_delins,
        Event.SUBSTITUTION: rna.validate_substitution,
    },
    Level.PROTEIN: {
        Event.INSERTION: protein.validate_insertion,
        Event.DELETION: protein.validate_deletion,
        Event.DELINS: protein.validate_delins,
        Event.SUBSTITUTION: protein.validate_substitution,
        Event.FRAME_SHIFT: protein.validate_frame_shift,
    }
}


def validate_multi_variant(hgvs, level=None):
    if not hgvs:
        return None
    if level and not isinstance(level, Level):
        raise TypeError(
            "`level` must be a valid Level enum. Found '{}'".format(
                type(level).__name__
            ))

    if hgvs in constants.wt_or_sy:
        return

    match = multi_variant_re.fullmatch(hgvs)
    if match:
        if not level:
            level = infer_level(hgvs)
        if level is None:
            raise ValidationError(
                "Variant '{}' has an unsupported prefix '{}'. "
                "Supported prefixes are 'cngmpr'.".format(hgvs, hgvs[0])
            )

        hgvs_ = hgvs[3:-1]  # removes prefix and square brackets
        if level == Level.RNA:
            if semi_colon_separated_re.match(hgvs_):
                matches = hgvs_.split(';')
            elif comma_separated_re.match(hgvs_):
                matches = hgvs_.split(',')
            else:
                raise ValidationError(
                    "RNA multi-variant '{}' contains an unknown delimiter. "
                    "Supported delimiters are ';' and ','.".format(hgvs)
                )
        else:
            matches = hgvs_.split(';')

        # This probably isn't needed since the regex has already matched.
        # Use for validating capture groups within each match but currently
        # capture groups are not checked against HGVS guidelines.
        for event in matches:
            if event in constants.wt_or_sy:
                continue
            type_ = infer_type(event)
            validate_event_functions[level][type_](event)
    else:
        raise ValidationError(
            "'{}' is not a supported HGVS syntax.".format(hgvs))


def validate_single_variant(hgvs, level=None):
    if not hgvs:
        return None
    if level and not isinstance(level, Level):
        raise TypeError(
            "`level` must be a valid Level enum. Found '{}'".format(
                type(level).__name__
            ))

    if hgvs in constants.wt_or_sy:
        return
    match = single_variant_re.fullmatch(hgvs)
    if match:
        type_ = infer_type(hgvs)
        if not level:
            level = infer_level(hgvs)
        if type_ is None or level is None:
            raise ValidationError(
                "'{}' is not a supported HGVS syntax.".format(hgvs))
        validate_event_functions[level][type_](hgvs)
    else:
        raise ValidationError(
            "'{}' is not a supported HGVS syntax.".format(hgvs))