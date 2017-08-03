import re
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError

SCS_ACCESSION_RE = r'SCS\d{6}[A-Z]+.\d+'
VAR_ACCESSION_RE = r'SCSVAR\d{6}[A-Z]+.\d+.\d+'


def valid_scs_accession(accession):
    if not re.match(SCS_ACCESSION_RE, accession):
        raise ValidationError(
            _("%(accession)s is not a valid ScoreSet accession."),
            params={"accession": accession}
        )


def valid_var_accession(accession):
    if not re.match(VAR_ACCESSION_RE, accession):
        raise ValidationError(
            _("%(accession)s is not a valid Variant accession."),
            params={"accession": accession}
        )


def valid_hgvs_string(string):
    pass


def valid_json_field(json_object):
    from .models import SCORES_KEY, COUNTS_KEY
    if SCORES_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the key %(key)s."),
            params={"data": json_object, "key": SCORES_KEY}
        )
    if COUNTS_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the key %(key)s."),
            params={"data": json_object, "key": COUNTS_KEY}
        )
    expected = sorted([SCORES_KEY, COUNTS_KEY])
    extras = [k for k in json_object.keys() if k not in expected]
    if len(extras) > 0:
        extras = [k for k in json_object.keys() if k not in expected]
        raise ValidationError(
            _("%(data)s has additional keys %(extras)s."),
            params={"data": json_object, "extras": extras}
        )
