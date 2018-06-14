import re

from django.core.exceptions import ValidationError


#: Conversions between single- and three-letter amino acid codes
AA_CODES = {
        'Ala' : 'A', 'A' : 'Ala',
        'Arg' : 'R', 'R' : 'Arg',
        'Asn' : 'N', 'N' : 'Asn',
        'Asp' : 'D', 'D' : 'Asp',
        'Cys' : 'C', 'C' : 'Cys',
        'Glu' : 'E', 'E' : 'Glu',
        'Gln' : 'Q', 'Q' : 'Gln',
        'Gly' : 'G', 'G' : 'Gly',
        'His' : 'H', 'H' : 'His',
        'Ile' : 'I', 'I' : 'Ile',
        'Leu' : 'L', 'L' : 'Leu',
        'Lys' : 'K', 'K' : 'Lys',
        'Met' : 'M', 'M' : 'Met',
        'Phe' : 'F', 'F' : 'Phe',
        'Pro' : 'P', 'P' : 'Pro',
        'Ser' : 'S', 'S' : 'Ser',
        'Thr' : 'T', 'T' : 'Thr',
        'Trp' : 'W', 'W' : 'Trp',
        'Tyr' : 'Y', 'Y' : 'Tyr',
        'Val' : 'V', 'V' : 'Val',
        'Ter' : '*', '*' : 'Ter',
}

AA_TRI = set(AA_CODES.keys())
amino_acids = '|'.join(AA_TRI).replace('?', '\?')


utr_descriptor = r"(?P<utr>[*-])"
position = r"(?:((\d+)|\?|([*-]?\d+([\+-]?(\d+|\?))?)))"
interval = r"(?:(({0})_({0})))".format(position)
fragment = r"(?:\({0}\))".format(interval)
breakpoint_ = r"(?:({0}_{0}))".format(fragment)


# Expression with capture groups
deletion = (
    r"(?P<del>"
        r"("
            r"((?P<aa_start>{0})(?P<start>\d+)_(?P<aa_end>{0})(?P<end>\d+))"
            r"|"
            r"((?P<aa>{0})(?P<pos>\d+)(?P<mosaic>\=/)?)"
        r")"
        r"del"
    r")".format(amino_acids)
)
insertion = (
    r"(?P<ins>"
        r"(?P<aa_start>{0})(?P<start>\d+)_(?P<aa_end>{0})(?P<end>\d+)"
        r"ins"
        r"("
            r"(?P<aas>[{0}]+)"
            r"|"
            r"(?P<length>\d+)"
            r"|"
            r"(?P<unknown>(\(\d+\))|X+)"
        r")"
    r")".format(amino_acids)
)
delins = (
    r"(?P<delins>"
        r"((?P<aa_start>{0})(?P<start>\d+)(_(?P<aa_end>{0})(?P<end>\d+))?)"
        r"delins"
        r"("
            r"(?P<aas>[{0}]+)"
            r"|"
            r"(?P<length>\d+)"
            r"|"
            r"(?P<unknown>X+)"
        r")"
    r")".format(amino_acids)
)
substitution = (
    r"(?P<sub>"
        r"((?P<no_protein>0)|(?P<unknown>\?))"
        r"|"
        r"("
            r"(?P<ref>{0})(?P<pos>\d+)"
            r"("
                r"(?P<new>((?P<mosaic>\=/)?({0}))|(({0}){{1}}(\^({0}))+(?!\^))|(\*))"
                r"|"
                r"(?P<silent>\=)"
            r")"
        r")"
    r")".format(amino_acids)
)
frame_shift = (
    r"(?P<fs>"
        r"(?P<aa_1>{0})(?P<pos>\d+)(?P<aa_2>{0})fs"
        r"(?P<shift>"
            r"(({0})(\d+))"
            r"(\*\?)"
            r"(\*\d+)"
        r")?"
    r")"
).format(amino_acids)

# Expression capture groups used for joining and multi-variant matching
# where re-defined capture groups are not valid regex.
any_event = r"({0})?({1})".format(
    utr_descriptor,
    r"|".join([insertion, deletion, delins, substitution, frame_shift]))
any_event, _ = re.subn(r"P<\w+(_\w+)?>", ':', any_event)
single_variant = r"(p\.{0})|(p.\({0}\))".format(any_event)
multi_variant =  r"p\.\[({0})(;{0}){{1,}}(?!;)\]".format(any_event)

# ---- Compiled Regexes
deletion_re = re.compile(
    r"(?P<prefix>p\.)?({0})?({1})".format(utr_descriptor, deletion))
insertion_re = re.compile(
    r"(?P<prefix>p\.)?({0})?({1})".format(utr_descriptor, insertion))
delins_re = re.compile(
    r"(?P<prefix>p\.)?({0})?({1})".format(utr_descriptor, delins))
substitution_re = re.compile(
    r"(?P<prefix>p\.)?({0})?({1})".format(utr_descriptor, substitution))
frame_shift_re = re.compile(
    r"(?P<prefix>p\.)?({0})?({1})".format(utr_descriptor, frame_shift))
single_variant_re = re.compile(single_variant)
multi_variant_re = re.compile(multi_variant)


def split_amino_acids(aa_str):
    return re.findall('[A-Z][^A-Z]*', aa_str)


def validate_substitution(hgvs):
    match = substitution_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported substitution syntax.".format(hgvs))
    
    ref = match.groupdict().get('ref', None)
    new = match.groupdict().get('new', None)
    
    silent = match.groupdict().get('silent', False)
    unknown = match.groupdict().get('unknown', False)
    no_protein = match.groupdict().get('no_protein', False)
    
    if not (silent or unknown or no_protein):
        if (ref is not None and new is not None) and ref == new:
            raise ValidationError(
                "Reference amino acid cannot be the same as the "
                "new amino acid for variant '{}'. This should be described"
                "as a silent variant 'p.{}='.".format(match.string, ref)
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


def validate_frame_shift(hgvs):
    match = frame_shift_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported frame shift syntax.".format(hgvs))
    
    aa_2 = match.groupdict().get('aa_2', None)
    if aa_2 and aa_2 in ('Ter', '*'):
        raise ValidationError(
            "Amino acid '{}' preceeding 'fs' in a frame shift cannot "
            "be 'Ter' or '*'.".format(aa_2))
    