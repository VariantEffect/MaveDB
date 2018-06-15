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
amino_acids = '({})'.format(
    '|'.join(AA_TRI).replace('?', '\?').replace('*', '\*')
)


position = r"(?:(({0})\d+)|\?)".format(amino_acids)
interval = r"(?:(({0})_({0})))".format(position)
amino_acid_choice = r"(?:({0}){{1}}(\^({0}))+(?!\^))".format(amino_acids)


# Expression with capture groups
deletion = (
    r"(?P<del>"
        r"("
            r"(?P<interval>{0})"
            r"|"
            r"((?P<position>{1})(?P<mosaic>\=/)?)"
        r")"
        r"del"
    r")".format(interval, position)
)
insertion = (
    r"(?P<ins>"
        r"(?P<interval>{0})"
        r"ins"
        r"("
            r"(?P<inserted>{1}+|{2})"
            r"|"
            r"(?P<length>\d+)"
            r"|"
            r"(?P<unknown>(\(\d+\))|X+)"
        r")"
    r")".format(interval, amino_acids, amino_acid_choice)
)
delins = (
    r"(?P<delins>"
        r"("
            r"(?P<interval>{0})"
            r"|"
            r"(?P<position>{1})"
        r")"
        r"delins"
        r"("
            r"(?P<inserted>{2}+|{3})"
            r"|"
            r"(?P<length>\d+)"
            r"|"
            r"(?P<unknown>(\(\d+\))|X+)"
        r")"
    r")".format(interval, position, amino_acids, amino_acid_choice)
)
substitution = (
    r"(?P<sub>"
        r"((?P<no_protein>0)|(?P<not_predicted>\?))"
        r"|"
        r"("
            r"(?P<ref>{0})(?P<pos>\d+)"
            r"("
                r"(?P<new>((?P<mosaic>\=/)?({0}))|(?P<choice>{1})|(\*))"
                r"|"
                r"(?P<silent>\=)"
                r"|"
                r"(?P<unknown>\?)"
            r")"
        r")"
    r")".format(amino_acids, amino_acid_choice)
)
frame_shift = (
    r"(?P<fs>"
        r"(?P<left_aa>{0})(?P<position>\d+)(?P<right_aa>{0})?fs"
        r"(?P<shift>"
            r"("
                r"({0}\d+)"
                r"|"
                r"(\*\?)"
                r"|"
                r"(\*\d+)"
            r")"
        r")?"
    r")"
).format(amino_acids)


# Expression capture groups used for joining and multi-variant matching
# where re-defined capture groups are not valid regex.
any_event = r"({0})".format(
    r"|".join([insertion, deletion, delins, substitution, frame_shift])
)
any_event, _ = re.subn(r"P<\w+(_\w+)?>", ':', any_event)
predicted_variant = r"p.\({0}\)".format(any_event)
single_variant = r"(p\.{0})|({1})".format(any_event, predicted_variant)
multi_variant =  r"p\.\[({0})(;{0}){{1,}}(?!;)\]".format(any_event)


# ---- Compiled Regexes
deletion_re = re.compile(r"(p\.)?({0})".format(deletion))
insertion_re = re.compile(r"(p\.)?({0})".format(insertion))
delins_re = re.compile(r"(p\.)?({0})".format(delins))
substitution_re = re.compile(r"(p\.)?({0})".format(substitution))
frame_shift_re = re.compile(r"(p\.)?({0})".format(frame_shift))

single_variant_re = re.compile(single_variant)
multi_variant_re = re.compile(multi_variant)
any_event_re = re.compile(any_event)
predicted_variant_re = re.compile(predicted_variant)


def split_amino_acids(aa_str):
    return re.findall('[A-Z][^A-Z]*', aa_str)


def validate_substitution(hgvs):
    if predicted_variant_re.match(hgvs):
        match = substitution_re.fullmatch(hgvs[3:-1])
    else:
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
    if predicted_variant_re.match(hgvs):
        match = deletion_re.fullmatch(hgvs[3:-1])
    else:
        match = deletion_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported deletion syntax.".format(hgvs))


def validate_insertion(hgvs):
    if predicted_variant_re.match(hgvs):
        match = insertion_re.fullmatch(hgvs[3:-1])
    else:
        match = insertion_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported insertion syntax.".format(hgvs))


def validate_delins(hgvs):
    if predicted_variant_re.match(hgvs):
        match = delins_re.fullmatch(hgvs[3:-1])
    else:
        match = delins_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported deletion-insertion syntax.".format(hgvs))


def validate_frame_shift(hgvs):
    if predicted_variant_re.match(hgvs):
        match = frame_shift_re.fullmatch(hgvs[3:-1])
    else:
        match = frame_shift_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported frame shift syntax.".format(hgvs))
    
    aa_2 = match.groupdict().get('aa_2', None)
    if aa_2 and aa_2 in ('Ter', '*'):
        raise ValidationError(
            "Amino acid '{}' preceeding 'fs' in a frame shift cannot "
            "be 'Ter' or '*'.".format(aa_2))
    