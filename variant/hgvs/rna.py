import re

from django.core.exceptions import ValidationError

from . import parse_positions, utr_descriptor, validate_event

from .dna import deletion as dna_deletion
from .dna import insertion as dna_insertion
from .dna import delins as dna_delins
from .dna import substitution as dna_substitution
from .dna import any_event as dna_any_event
from .dna import any_event_type as dna_any_event_type

nucleotides = 'augcxn'

# Expression with capture groups
deletion = dna_deletion.replace('ATCGXN', nucleotides)
insertion = dna_insertion.replace('ATCGXN', nucleotides)
delins = dna_delins.replace('ATCGXN', nucleotides)
substitution = dna_substitution.replace('ATCGXN', nucleotides)
any_event = dna_any_event.replace('ATCGXN', nucleotides)
any_event_type = dna_any_event_type.replace('ATCGXN', nucleotides)

# ---- Compiled Regexes
deletion_re = re.compile(
    r"(?P<prefix>r\.)?({0})?({1})".format(utr_descriptor, deletion))
insertion_re = re.compile(
    r"(?P<prefix>r\.)?({0})?({1})".format(utr_descriptor, insertion))
delins_re = re.compile(
    r"(?P<prefix>r\.)?({0})?({1})".format(utr_descriptor, delins))
substitution_re = re.compile(
    r"(?P<prefix>r\.)?({0})?({1})".format(utr_descriptor, substitution))


def validate_substitution(event):
    event = validate_event(event, regex=substitution_re)
    ref_nt = event.groupdict().get('ref', None)
    new_nt = event.groupdict().get('new', None)
    if not ref_nt or not new_nt:
        raise ValidationError(
            "Invalid nucleotides for variant '{}'".format(event.string)
        )
    if ref_nt == new_nt:
        raise ValidationError(
            "Reference nucleotide cannot be the same as the "
            "new nucleotide for variant '{}'.".format(event.string)
        )


def validate_deletion(event):
    event = validate_event(event, regex=deletion_re)
    start = event.groupdict().get('start', None)
    end = event.groupdict().get('end', None)
    single = event.groupdict().get('del_single', False)
    base = event.groupdict().get('base', None)
    if (start is None or end is None) and not single:
        raise ValidationError("Invalid deletion variant '{}',".format(
            event.string))
    if single and not base:
        raise ValidationError(
            "Single base deletion variant '{}' must specify "
            "the deleted base.".format(event.string)
        )
    if not single:
        start, end = parse_positions(start, end)
        if start >= end:
            raise ValidationError(
                "Deletion starting position must be less than the ending "
                "position in variant '{}'.".format(event.string)
            )


def validate_insertion(event):
    event = validate_event(event, regex=insertion_re)
    start = event.groupdict().get('start', None)
    end = event.groupdict().get('end', None)
    if start is None or end is None:
        raise ValidationError("Invalid insertion variant '{}',".format(
            event.string))
    
    start, end = parse_positions(start, end)
    if start >= end:
        raise ValidationError(
            "Insertion starting position must be less than the ending "
            "position in variant '{}'.".format(event.string)
        )
    flanking = start == (end - 1)
    if not flanking:
        raise ValidationError(
            "Interval must define a flanking insertion site in '{}'.".format(
                event.string)
        )


def validate_delins(event):
    event = validate_event(event, regex=delins_re)
    start = event.groupdict().get('start', None)
    end = event.groupdict().get('end', None)
    if start is None or end is None:
        raise ValidationError("Invalid indel variant '{}',".format(
            event.string))
    
    start, end = parse_positions(start, end)
    if start >= end:
        raise ValidationError(
            "Indel starting position must be less than the ending "
            "position in variant '{}'.".format(event.string)
        )
