import re
from enum import Enum

from django.core.exceptions import ValidationError

from .dna import validate_deletion as dna_validate_deletion
from .dna import validate_insertion as dna_validate_insertion
from .dna import validate_delins as dna_validate_delins
from .dna import validate_substitution as dna_validate_substitution

from .rna import validate_deletion as rna_validate_deletion
from .rna import validate_insertion as rna_validate_insertion
from .rna import validate_delins as rna_validate_delins
from .rna import validate_substitution as rna_validate_substitution

from .protein import *


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
utr_descriptor = r"(?P<utr>[*-])"
position = r"(\d+)|(\d+(\+|-)\d+)"

single_variant = r"[cngmrp]\.{event}".format(event=any_event_type)
multi_variant = r"[cngmrp]\.\[({event})(;{event}){{1,}}(?!;)\]".format(
    event=any_event)

any_event_type_re = re.compile(any_event_type)
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
    
    },
    Level.PROTEIN: {
    
    }
}


def is_multi(hgvs):
    return bool(multi_variant_re.fullmatch(hgvs))


def validate_event(event, regex):
    if isinstance(event, str):
        match = regex.fullmatch(event)
        if not match:
            raise ValidationError("Invalid variant '{}'.".format(event))
        return match
    elif hasattr(event, 'groupdict'):
        return event
    else:
        raise TypeError(
            "Expected `event` to be str or an re match object. "
            "Found {}.".format(type(event).__name__)
        )


def parse_positions(start, end):
    if start is None or end is None:
        return None, None
    start = re.split(r"[\+-]", start)
    end = re.split(r"[\+-]", end)
    intronic = any([len(x) >= 2 for x in [start, end]])
    if intronic and len(start) < 2:
        start = 1
    else:
        start = int(start[-1])
    if intronic and len(end) < 2:
        end = start + 1
    else:
        end = int(end[-1])
    return int(start), int(end)


def validate_multi_variant(hgvs):
    match = multi_variant_re.fullmatch(hgvs)
    if match:
        if hgvs[0] in 'cngm':
            level = Level.DNA
        elif hgvs[0] == 'r':
            level = Level.RNA
        elif hgvs[0] == 'p':
            level = Level.PROTEIN
        else:
            raise ValidationError(
                "Variant '{}' has an unsupported prefix '{}'. "
                "Supported prefixes are 'cngmp'".format(hgvs, hgvs[0])
            )
        validate_single_variants(hgvs or hgvs, level, multi=True)
    else:
        raise ValidationError("Invalid HGVS string '{}'.".format(hgvs))


def validate_single_variants(hgvs, level, multi=False):
    hgvs_ = hgvs  # Original variant left unmodified for error messages.
    if multi:
        hgvs_ = hgvs[3:-1]  # removes prefix and square brackets
    
    if not multi and level == Level.PROTEIN:
        # Strip the parentheses since the regex won't work with them.
        hgvs_ = hgvs_.replace('p.(', 'p.')
        if hgvs_[-1] == ')':
            hgvs_ = hgvs_[:-1]
    
    matches = hgvs_.split(';')
    if len(matches) != len(set(matches)):
        raise ValidationError(
            "Multi-variant '{}' has defined the same "
            "event more than once.".format(hgvs)
        )
    
    if matches:
        for event in matches:
            match = any_event_type_re.fullmatch(event)
            if not match:
                raise ValidationError(
                    "Invalid event '{}' in '{}'.".format(event, hgvs))
            
            if match.groupdict().get(Event.INSERTION.value, None):
                type_ = Event.INSERTION
            elif match.groupdict().get(Event.DELETION.value, None):
                type_ = Event.DELETION
            elif match.groupdict().get(Event.SUBSTITUTION.value, None):
                type_ = Event.SUBSTITUTION
            elif match.groupdict().get(Event.DELINS.value, None):
                type_ = Event.DELINS
            else:
                type_ = None
            
            if not type_:
                raise ValidationError(
                    "MaveDB does not currently support variants "
                    "with syntax like '{}'.".format(event)
                )
            validate_event_functions[level][type_](event)
    else:
        raise ValidationError(
            "Variant '{}' has an invalid "
            "multi-variant format. "
            "Check that events are "
            "semi-colon delimited.".format(hgvs)
        )
