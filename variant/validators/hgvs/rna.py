from hgvsp.dna import substitution_re, delins_re, deletion_re, insertion_re

from django.core.exceptions import ValidationError


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
