
import re
from io import StringIO

from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError


SCS_ACCESSION_RE = r'SCS\d{6}[A-Z]+.\d+'
VAR_ACCESSION_RE = r'SCSVAR\d{6}[A-Z]+.\d+.\d+'


#: Matches a single amino acid substitution in HGVS_ format.
re_protein = re.compile(
    "(?P<match>p\.(?P<pre>[A-Z][a-z][a-z])(?P<pos>-?\d+)"
    "(?P<post>[A-Z][a-z][a-z]))")


#: Matches a single nucleotide substitution (coding or noncoding)
#: in HGVS_ format.
re_nucleotide = re.compile(
    "(?P<match>[nc]\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")


#: Matches a single coding nucleotide substitution in HGVS_ format.
re_coding = re.compile(
    "(?P<match>c\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]) "
    "\(p\.(?:=|[A-Z][a-z][a-z]-?\d+[A-Z][a-z][a-z])\))")


#: Matches a single noncoding nucleotide substitution in HGVS_ format.
re_noncoding = re.compile(
    "(?P<match>n\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")


class Constants(object):
    NAN_COL_VALUES = set(['nan', 'na', 'none', ''])
    HGVS_COLUMN = "hgvs"
    COUNT_COLUMN = "count"
    SCORES_DATA = "scores_data"
    COUNTS_DATA = "counts_data"


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
#    variants = [v.strip() for v in string.strip().split(',')]
#
#    protein_matches = all([re_protein.match(v) for v in variants])
#    nucleotide_matches = all([re_nucleotide.match(v) for v in variants])
#    coding_matches = all([re_coding.match(v) for v in variants])
#    noncoding_matches = all([re_noncoding.match(v) for v in variants])
#    wt_or_sy = all([v in ["_wt", "_sy"] for v in variants])
#
#    if not (protein_matches or nucleotide_matches or
#            coding_matches or noncoding_matches or wt_or_sy):
#        raise ValidationError(
#            _("Variant '%(variant)s' is not a valid HGVS string."),
#            params={'variant': string}
#        )
    return


def valid_scoreset_score_data_input(file):
    from .forms import Constants

    header_line = file.readline()
    if isinstance(header_line, bytes):
        header_line = header_line.decode()

    expected_header = [Constants.HGVS_COLUMN]
    header = [l.strip() for l in header_line.strip().split(',')]
    try:
        valid_header = header[0] == expected_header[0]
        if not valid_header:
            raise ValueError()
    except:
        raise ValidationError(
            _(
                "Score data header requires the column 'hgvs'. Ensure the "
                "columns are separated by a comma, and that 'hgvs' is the "
                "first column."
            )
        )
    if file.size < 4:
        raise ValidationError(_("Dataset cannot be empty."))


def valid_scoreset_count_data_input(file):
    from .forms import Constants

    header_line = file.readline()
    if isinstance(header_line, bytes):
        header_line = header_line.decode()

    expected_header = [Constants.HGVS_COLUMN]
    header = [l.strip() for l in header_line.strip().split(',')]
    try:
        valid_header = (header[0] == expected_header[0])
        if not valid_header:
            raise ValueError()
    except:
        raise ValidationError(
            _(
                "Count data header requires the column 'hgvs'. Ensure the "
                "columns are separated by a comma, and that 'hgvs' is the "
                "first column."
            )
        )
    if file.size < 4:
        raise ValidationError(_("Dataset cannot be empty."))


def valid_scoreset_json(json_object, has_counts_data=False):
    from .models import SCORES_KEY, COUNTS_KEY
    if SCORES_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": SCORES_KEY}
        )
    if COUNTS_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": COUNTS_KEY}
        )
    expected = [SCORES_KEY, COUNTS_KEY]
    extras = [k for k in json_object.keys() if k not in set(expected)]
    if len(extras) > 0:
        extras = [k for k in json_object.keys() if k not in expected]
        raise ValidationError(
            _("%(data)s has additional unexpected keys '%(extras)s'."),
            params={"data": json_object, "extras": extras}
        )

    # Check the correct data types are given.
    if not isinstance(json_object[SCORES_KEY], list):
        type_ = type(json_object[SCORES_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a list not %(type)s."),
            params={"data": json_object, "type": type_}
        )
    if not isinstance(json_object[COUNTS_KEY], list):
        type_ = type(json_object[COUNTS_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a list not %(type)s."),
            params={"data": json_object, "type": type_}
        )

    # Check the correct inner data types are given.
    try:
        if not isinstance(json_object[SCORES_KEY][0], str):
            raise ValidationError("")
    except IndexError:
        raise ValidationError(
            _("No header could be found for '%(key)s' dataset."),
            params={"key": SCORES_KEY}
        )
    except ValidationError:
        type_ = type(json_object[SCORES_KEY][0]).__name__
        raise ValidationError(
            _("Header values must be strings not '%(type)s'."),
            params={"type": type_}
        )

    try:
        if not isinstance(json_object[COUNTS_KEY][0], str):
            raise ValidationError()
    except IndexError:
        if has_counts_data:
            raise ValidationError(
                _("No header could be found for '%(key)s' dataset."),
                params={"key": COUNTS_KEY}
            )
    except ValidationError:
        type_ = type(json_object[COUNTS_KEY][0]).__name__
        raise ValidationError(
            _("Header values must be strings not '%(type)s'."),
            params={"type": type_}
        )


def valid_variant_json(json_object):
    from .models import SCORES_KEY, COUNTS_KEY
    if SCORES_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": SCORES_KEY}
        )
    if COUNTS_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": COUNTS_KEY}
        )
    expected = [SCORES_KEY, COUNTS_KEY]
    extras = [k for k in json_object.keys() if k not in set(expected)]
    if len(extras) > 0:
        extras = [k for k in json_object.keys() if k not in expected]
        raise ValidationError(
            _("%(data)s has additional unexpected keys '%(extras)s'."),
            params={"data": json_object, "extras": extras}
        )

    # Check the correct data types are given.
    if not isinstance(json_object[SCORES_KEY], dict):
        type_ = type(json_object[SCORES_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a dict not %(type)s."),
            params={"data": json_object, "type": type_}
        )
    if not isinstance(json_object[COUNTS_KEY], dict):
        type_ = type(json_object[COUNTS_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a dict not %(type)s."),
            params={"data": json_object, "type": type_}
        )
