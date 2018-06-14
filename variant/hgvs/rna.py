import re

from django.core.exceptions import ValidationError


nucleotides = 'augcxnh'
utr_descriptor = r"(?P<utr>[*-])"
position = r"(?:(\d+)|\?)"
interval = r"(?:(({0})_({0})))".format(position)
fragment = r"(?:\({0}\))".format(interval)
intronic_position = r"(?:((\d+)|\?|\d+([\+-]?(\d+|\?))?))"
intronic_interval = r"(?:(({0})_({0})))".format(intronic_position)

# Expression with capture groups
edge_cases = r"(0|spl|\?)"
deletion = (
    r"(?P<del>"
        r"(((\=/)|(\=//))?(?P<interval>{0})del)"
        r"|"
        r"((?P<fragment>{1})del)"
        r"|"
        r"((?P<position>{2})del(?P<base>[{3}])?)"
    r")".format(interval, fragment, position, nucleotides)
)
insertion = (
    r"(?P<ins>"
        r"((?P<interval>{0})|(?P<fragment>{1}))"
        r"ins"
        r"("
            r"(?P<intronic>\[({2})(;{2}){{1,}}(?!;)\])"
            r"|"
            r"((?P<bases>[{3}]+)|(?P<length>\(\d+\)))"
        r")"
    r")".format(interval, fragment, intronic_interval, nucleotides)
)
delins = (
    r"(?P<delins>"
        r"("
            r"((?P<interval>{0})delins)"
            r"|"
            r"((?P<position>{1})delins)"
        r")"
        r"((?P<bases>[{2}]+)|(?P<length>\(\d+\)))"
    r")".format(interval, position, nucleotides)
)
substitution = (
    r"(?P<sub>"
        r"("
            r"(0|\?|spl)"
            r"|"
            r"("
                r"(?P<position>{0})"
                r"("
                    r"((?P<mosaic>(\=/)|(\=//))?(?P<ref>[{1}])>(?P<new>[{1}]))"
                    r"|"
                    r"(?P<silent>\=)"
                r")"
            r")"
        r")"
    r")".format(position, nucleotides)
)

# Expression capture groups used for joining and multi-variant matching
# where re-defined capture groups are not valid regex.
any_event = r"({})".format(
    r"|".join([insertion, deletion, delins, substitution]))
any_event, _ = re.subn(r"P<\w+(_\w+)?>", ':', any_event)

single_variant = r"r\.{0}".format(any_event)
multi_variant =  (
    r"r\.((\[({0})(;{0}){{1,}}(?!;)\])|(\[({0})(,{0}){{1,}}(?!,)\]))".format(
        any_event)
)

# ---- Compiled Regexes
deletion_re = re.compile(
    r"(r\.)?({0})?({1})".format(utr_descriptor, deletion))
insertion_re = re.compile(
    r"(r\.)?({0})?({1})".format(utr_descriptor, insertion))
delins_re = re.compile(
    r"(r\.)?({0})?({1})".format(utr_descriptor, delins))
substitution_re = re.compile(
    r"(r\.)?({0})?({1})".format(utr_descriptor, substitution))
single_variant_re = re.compile(single_variant)
multi_variant_re = re.compile(multi_variant)


def validate_substitution(hgvs):
    match = substitution_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported substitution syntax.".format(hgvs))
    ref_nt = match.groupdict().get('ref', None)
    new_nt = match.groupdict().get('new', None)
    silent = match.groupdict().get('silent', None)
    if not silent and (ref_nt is not None and new_nt is not None):
        if ref_nt == new_nt:
            raise ValidationError(
                "Reference nucleotide cannot be the same as the "
                "new nucleotide for variant '{}'.".format(hgvs)
            )


def validate_deletion(hgvs):
    match = deletion_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported deletion syntax.".format(hgvs))


def validate_insertion(hgvs):
    match = insertion_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported insertion syntax.".format(hgvs))
    

def validate_delins(hgvs):
    match = delins_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported deletion-insertion syntax.".format(hgvs))
