"""
HGVS regex parsing for DNA, RNA and Protein specifications. `Event` refers
to a specific mutation event which does not contain any prefixes i.e.
a character from 'pcngmr' prefixing a mutation syntax like p.Leu4Gly. A
`variant` refers to an `Event` prefixed with a the former characters, which
may also be enclosed in parentheses or brackets e.g. p.(Leu5Gly)
or p.[Leu4Gly;Gly7Leu]
"""

import re
from enum import Enum

from django.core.exceptions import ValidationError

from .dna import validate_deletion as dna_validate_deletion
from .dna import validate_insertion as dna_validate_insertion
from .dna import validate_delins as dna_validate_delins
from .dna import validate_substitution as dna_validate_substitution
from .dna import single_variant as dna_single_variant
from .dna import multi_variant as dna_multi_variant
from .dna import any_event_re as dna_any_event_re

from .rna import validate_deletion as rna_validate_deletion
from .rna import validate_insertion as rna_validate_insertion
from .rna import validate_delins as rna_validate_delins
from .rna import validate_substitution as rna_validate_substitution
from .rna import single_variant as rna_single_variant
from .rna import multi_variant as rna_multi_variant
from .rna import comma_separated_re as rna_comma_separated_re
from .rna import semi_colon_separated_re as rna_semi_colon_separated_re
from .rna import any_event_re as rna_any_event_re

from .protein import validate_deletion as protein_validate_deletion
from .protein import validate_insertion as protein_validate_insertion
from .protein import validate_delins as protein_validate_delins
from .protein import validate_substitution as protein_validate_substitution
from .protein import validate_frame_shift as protein_validate_frame_shift
from .protein import single_variant as protein_single_variant
from .protein import multi_variant as protein_multi_variant
from .protein import any_event_re as protein_any_event_re


class Event(Enum):
    DELETION = 'del'
    INSERTION = 'ins'
    DELINS = 'delins'
    SUBSTITUTION = 'sub'
    FRAME_SHIFT = 'fs'
    
    @classmethod
    def str_to_enum(cls, item):
        if item[0] in ['>', '=', '=//', '=/']:
            return cls.SUBSTITUTION
        else:
            return cls._value2member_map_.get(item, None)


class Level(Enum):
    DNA = 'dna'
    RNA = 'rna'
    PROTEIN = 'protein'
    
    @classmethod
    def str_to_enum(cls, item):
        return cls._value2member_map_.get(item, None)


# Expression capture groups used for joining and multi-variant matching
# where re-defined capture groups are not valid regex.
single_variant = r"({0})|({1})|({2})".format(
    dna_single_variant,
    rna_single_variant,
    protein_single_variant,
)
multi_variant = r"({0})|({1})|({2})".format(
    dna_multi_variant,
    rna_multi_variant,
    protein_multi_variant,
)


# ---- Compiled Regex Expressions
single_variant_re = re.compile(single_variant)
multi_variant_re = re.compile(multi_variant)


validate_event_functions = {
    Level.DNA: {
        Event.INSERTION: dna_validate_insertion,
        Event.DELETION: dna_validate_deletion,
        Event.DELINS: dna_validate_delins,
        Event.SUBSTITUTION: dna_validate_substitution,
    },
    Level.RNA: {
        Event.INSERTION: rna_validate_insertion,
        Event.DELETION: rna_validate_deletion,
        Event.DELINS: rna_validate_delins,
        Event.SUBSTITUTION: rna_validate_substitution,
    },
    Level.PROTEIN: {
        Event.INSERTION: protein_validate_insertion,
        Event.DELETION: protein_validate_deletion,
        Event.DELINS: protein_validate_delins,
        Event.SUBSTITUTION: protein_validate_substitution,
        Event.FRAME_SHIFT: protein_validate_frame_shift,
    }
}


def infer_type(hgvs):
    """
    Infer the type of hgvs variant as supported by `Event`. The order of
    this if/elif block is important: DELINS should come before INSERTION and
    DELETION since DELINS events contain INSERTION and DELETION event values
    as substrings.
    
    Parameters
    ----------
    hgvs : str
        The hgvs string to infer from.
    
    Returns
    -------
    `Event`
        An `Enum` value from the `Event` enum.
    """
    if Event.DELINS.value in hgvs:
        return Event.DELINS
    elif Event.INSERTION.value in hgvs:
        return Event.INSERTION
    elif Event.DELETION.value in hgvs:
        return Event.DELETION
    elif Event.FRAME_SHIFT.value in hgvs:
        return Event.FRAME_SHIFT
    else:
        return Event.SUBSTITUTION
    
    
def infer_level(hgvs):
    """
    Infer the level of hgvs variant as supported by `Level` by inspecting
    the prefix.

    Parameters
    ----------
    hgvs : str
        The hgvs string to infer from.

    Returns
    -------
    `Level`
        An `Enum` value from the `Level` enum.
    """
    if hgvs[0] in 'cgnm':
        return Level.DNA
    elif hgvs[0] == 'r':
        return Level.RNA
    elif hgvs[0] == 'p':
        return Level.PROTEIN
    else:
        return None
    

def is_multi(hgvs):
    return bool(multi_variant_re.fullmatch(hgvs))


def validate_multi_variant(hgvs):
    match = multi_variant_re.fullmatch(hgvs)
    if match:
        level = infer_level(hgvs)
        if level is None:
            raise ValidationError(
                "Variant '{}' has an unsupported prefix '{}'. "
                "Supported prefixes are 'cngmpr'.".format(hgvs, hgvs[0])
            )

        hgvs_ = hgvs[3:-1]  # removes prefix and square brackets
        if level == Level.PROTEIN:
            # Strip the parentheses since the regex won't work with them.
            hgvs_ = hgvs_.replace('p.(', 'p.')
            if hgvs_[-1] == ')':
                hgvs_ = hgvs_[:-1]

        if level == Level.RNA:
            if rna_semi_colon_separated_re.match(hgvs_):
                matches = hgvs_.split(';')
            elif rna_comma_separated_re.match(hgvs_):
                matches = hgvs_.split(',')
            else:
                raise ValidationError(
                    "RNA multi-variant '{}' contains an unknown delimiter. "
                    "Supported delimiters are ';' and ','.")
        else:
            matches = hgvs_.split(';')

        if len(matches) != len(set(matches)):
            raise ValidationError(
                "Multi-variant '{}' has defined the same "
                "event more than once.".format(hgvs)
            )
        for event in matches:
            if event in ('_wt', '_sy'):
                continue
            type_ = infer_type(event)
            validate_event_functions[level][type_](event)
    else:
        raise ValidationError(
            "'{}' is not a supported HGVS syntax.".format(hgvs))
    
    
def validate_single_variants(hgvs):
    if hgvs in ('_wt', '_sy'):
        return
    type_ = infer_type(hgvs)
    level = infer_level(hgvs)
    if type_ is None or level is None:
        raise ValidationError(
            "'{}' is not a supported HGVS syntax.".format(hgvs))
    validate_event_functions[level][type_](hgvs)
