import re

from django.core.exceptions import ValidationError

from . import parse_positions, position, utr_descriptor, validate_event


nucleotides = 'ATCGXN'


# Expression with capture groups
deletion = (
    r"(?P<start>{0})_(?P<end>{0})(?P<del>del)"
    r"|"
    r"(?P<pos>{0})(?P<del_single>del)(?P<base>[{1}])".format(
        position, nucleotides)
)
insertion = (
    r"(?P<start>{0})_(?P<end>{0})(?P<ins>ins)"
    r"(?P<bases>[{1}]+)".format(position, nucleotides)
)
delins = (
    r"(?P<start>{0})_(?P<end>{0})(?P<delins>delins)"
    r"(?P<bases>[{1}]+)".format(position, nucleotides)
)
substitution = (
    r"(?P<sub>"
        r"(?P<pos>{0})"
        r"(?P<ref>[{1}])"
        r"("
            r"((>|\=/|\=//)(?P<new>[{1}]))"
            r"|"
            r"(?P<silent>\=)"
        r")"
    r")".format(position, nucleotides)
)

# Expression capture groups used for joining and multi-variant matching
# where re-defined capture groups are not valid regex.
any_event = r"({0})?({1})".format(
    utr_descriptor,
    r"|".join([insertion, deletion, delins, substitution]))
any_event, _ = re.subn(r"P<\w+(_\w+)?>", ':', any_event)

any_event_type = r"({0})?({1})".format(
    utr_descriptor,
    r"|".join([insertion, deletion, delins, substitution]))
any_event_type, _ = re.subn(
    r"P<(utr|base|end|start|pos|bases|ref|new|silent)>", ':', any_event_type)

# ---- Compiled Regexes
deletion_re = re.compile(
    r"(?P<prefix>[cngm]\.)?({0})?({1})".format(utr_descriptor, deletion))
insertion_re = re.compile(
    r"(?P<prefix>[cngm]\.)?({0})?({1})".format(utr_descriptor, insertion))
delins_re = re.compile(
    r"(?P<prefix>[cngm]\.)?({0})?({1})".format(utr_descriptor, delins))
substitution_re = re.compile(
    r"(?P<prefix>[cngm]\.)?({0})?({1})".format(utr_descriptor, substitution))


def validate_substitution(event):
    event = validate_event(event, regex=substitution_re)
    ref_nt = event.groupdict().get('ref', None)
    new_nt = event.groupdict().get('new', None)
    silent = event.groupdict().get('silent', None)
    if not silent:
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
