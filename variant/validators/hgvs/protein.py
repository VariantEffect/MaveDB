from hgvsp.protein import (
    substitution_re,
    delins_re,
    deletion_re,
    insertion_re,
    frame_shift_re,
)

from django.core.exceptions import ValidationError

from ... import constants


def validate_substitution(hgvs):
    match = substitution_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported substitution syntax.".format(hgvs)
        )

    ref = match.groupdict().get(constants.hgvsp_pro_ref, None)
    alt = match.groupdict().get(constants.hgvsp_pro_alt, None)

    silent = match.groupdict().get(constants.hgvsp_silent, False)
    unknown = match.groupdict().get(constants.hgvsp_unknown, False)
    no_protein = match.groupdict().get(constants.hgvsp_pro_no_protein, False)

    if not (silent or unknown or no_protein):
        if (ref is not None and alt is not None) and ref == alt:
            raise ValidationError(
                "Reference amino acid cannot be the same as the "
                "new amino acid for variant '{}'. This should be described"
                "as a silent variant 'p.{}='.".format(match.string, ref)
            )


def validate_deletion(hgvs):
    match = deletion_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported deletion syntax.".format(hgvs)
        )


def validate_insertion(hgvs):
    match = insertion_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported insertion syntax.".format(hgvs)
        )


def validate_delins(hgvs):
    match = delins_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported deletion-insertion syntax.".format(hgvs)
        )


def validate_frame_shift(hgvs):
    match = frame_shift_re.fullmatch(hgvs)
    if match is None:
        raise ValidationError(
            "'{}' is not a supported frame shift syntax.".format(hgvs)
        )
