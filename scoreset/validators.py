import re
from django.core.exceptions import ValidationError

SCS_ACCESSION_RE = r'SCS\d{6}[A-Z]+'


# ---------------------------------------------------------------------- #
#                       ScoreSet Validators
# ---------------------------------------------------------------------- #
def valid_scs_accession(accession):
    if not re.match(SCS_ACCESSION_RE, accession):
        raise ValidationError(
            _("%(accession)s is not a valid ScoreSet accession."),
            params={"accession": accession}
        )
