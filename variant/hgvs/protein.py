import re

from django.core.exceptions import ValidationError

from . import parse_positions, utr_descriptor, validate_event


def split_amino_acids(aa_str):
    return re.findall('[A-Z][^A-Z]*', aa_str)


#: Conversions between single- and three-letter amino acid codes
AA_CODES = {
        'Ala' : 'A',
        'Arg' : 'R',
        'Asn' : 'N',
        'Asp' : 'D',
        'Cys' : 'C',
        'Glu' : 'E',
        'Gln' : 'Q',
        'Gly' : 'G',
        'His' : 'H',
        'Ile' : 'I',
        'Leu' : 'L',
        'Lys' : 'K',
        'Met' : 'M',
        'Phe' : 'F',
        'Pro' : 'P',
        'Ser' : 'S',
        'Thr' : 'T',
        'Trp' : 'W',
        'Tyr' : 'Y',
        'Val' : 'V',
        'Ter' : '*',
}

AA_TRI = set(AA_CODES.keys())
amino_acids = '|'.join(AA_TRI).replace('?', '\?')

# Expression with capture groups
deletion = (
    r"("
        r"((?P<aa_start>{0})(?P<start>\d+)_(?P<aa_end>{0})(?P<end>\d+))"
        r"|"
        r"((?P<aa>{0})(?P<pos>\d+)(?P<mosaic>\=/)?)"
    r")"
    r"(?P<del>del)".format(amino_acids)
)
insertion = (
    r"(?P<aa_start>{0})(?P<start>\d+)_(?P<aa_end>{0})(?P<end>\d+)"
    r"(?P<ins>ins)"
    r"("
        r"(?P<aas>[{0}]+)"
        r"|"
        r"(?P<length>\d+)"
        r"|"
        r"(?P<unknown>(\(\d+\))|X+)"
    r")".format(amino_acids)
)
delins = (
    r"((?P<aa_start>{0})(?P<start>\d+)(_(?P<aa_end>{0})(?P<end>\d+))?)"
    r"(?P<delins>delins)"
    r"("
        r"(?P<aas>[{0}]+)"
        r"|"
        r"(?P<length>\d+)"
        r"|"
        r"(?P<unknown>X+)"
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

any_event_type = r"({0})?({1})".format(
    utr_descriptor,
    r"|".join([insertion, deletion, delins, substitution, frame_shift]))
any_event_type, _ = re.subn(
    r"P<(utr|length|silent|mosaic|no_protein|unknown|aas|aa_start|aa_end"
    r"|base|end|start|pos|bases|ref|new|aa|aa_1|aa_2|shift|fs)>", ':', any_event_type)

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


def validate_substitution(event):
    event = validate_event(event, regex=substitution_re)
    ref = event.groupdict().get('ref', None)
    new = event.groupdict().get('new', None)
    
    silent = event.groupdict.get('silent', False)
    unknown = event.groupdict.get('unknown', False)
    no_protein = event.groupdict.get('no_protein', False)
    
    if not (silent or unknown or no_protein):
        if ref is None or new is None:
            raise ValidationError(
                "Invalid amino acids in variant '{}'".format(event.string)
            )
        if ref == new:
            raise ValidationError(
                "Reference amino acid cannot be the same as the "
                "new amino acid for variant '{}'. This should be described"
                "as a silent event 'p.{}='.".format(event.string, ref)
            )


def validate_deletion(event):
    event = validate_event(event, regex=deletion_re)
    # Multi deletion event
    start = event.groupdict().get('start', None)
    end = event.groupdict().get('end', None)
    # Information regarding a single deletion
    single = event.groupdict().get('aa', False)
    # pos = event.groupdict.get('pos', None)
    deleted_aa = event.groupdict().get('aa', None)
    
    if not single:
        if start is None or end is None:
            raise ValidationError("Invalid deletion variant '{}',".format(
                event.string))
        start, end = parse_positions(start, end)
        if start >= end:
            raise ValidationError(
                "Deletion starting position must be less than the ending "
                "position in variant '{}'.".format(event.string))
        
    if single and not deleted_aa:
        raise ValidationError(
            "Variant '{}' must specify the deleted amino acid.".format(
                event.string)
        )


def validate_insertion(event):
    event = validate_event(event, regex=insertion_re)
    # Multi-insertion event
    start = event.groupdict().get('start', None)
    end = event.groupdict().get('end', None)
    
    # aas = event.groupdict().get('aas', None)
    # aa_start = event.groupdict().get('aa_start', None)
    # aa_end = event.groupdict().get('aa_end', None)
    
    # For when only length is specified
    # length = event.groupdict().get('length', None)
    
    # For when unknown amino acids are inserted
    # unknown = event.groupdict().get('unknown', None)
    
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
            "Inserstion must define flanking positions in '{}'.".format(
                event.string)
        )


def validate_delins(event):
    event = validate_event(event, regex=delins_re)
    start = event.groupdict().get('start', None)
    end = event.groupdict().get('end', None)
    
    single = (start is not None) and (end is None)
    
    # aas = event.groupdict().get('aas', None)
    # aa_start = event.groupdict().get('aa_start', None)
    # aa_end = event.groupdict().get('aa_end', None)

    # For when only length is specified
    # length = event.groupdict().get('length', None)

    # For when unknown amino acids are inserted
    # unknown = event.groupdict().get('unknown', None)
    
    if not single:
        if start is None or end is None:
            raise ValidationError("Invalid indel variant '{}',".format(
                event.string))
        
        start, end = parse_positions(start, end)
        if start >= end:
            raise ValidationError(
                "Indel starting position must be less than the ending "
                "position in variant '{}'.".format(event.string)
            )

def validate_frame_shift(event):
    event = validate_event(event, regex=frame_shift_re)
    # aa_1 = event.groupdict().get('aa_1', None)
    # pos_1 = event.groupdict().get('pos', None)
    aa_2 = event.groupdict().get('aa_2', None)
    # extra = event.groupdict().get('shift', None)
    
    if aa_2 and aa_2 == 'Ter':
        raise ValidationError(
            "Amino acid '{}' preceeding 'fs' in a frame shift cannot "
            "be 'Ter'.".format(aa_2))
    