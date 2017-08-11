
import re
from django.core.exceptions import ValidationError

DNA_SEQ_RE = r'[ATGCatgc]+'
EXP_ACCESSION_RE = r'EXP\d{6}[A-Z]+'
EXPS_ACCESSION_RE = r'EXPS\d{6}'


# ---------------------------------------------------------------------- #
#                       Experiment Validators
# ---------------------------------------------------------------------- #
def valid_exp_accession(accession):
    if not re.match(EXP_ACCESSION_RE, accession):
        raise ValidationError(
            "%(accession)s is not a valid accession.",
            params={"accession": accession}
        )


def valid_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_RE, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )


# ---------------------------------------------------------------------- #
#                       ExperimentSet Validators
# ---------------------------------------------------------------------- #
def valid_expset_accession(accession):
    if not re.match(EXPS_ACCESSION_RE, accession):
        raise ValidationError(
            "%(accession)s is not a valid accession.",
            params={"accession": accession}
        )
