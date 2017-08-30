
import re
from io import StringIO

from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError


SCS_ACCESSION_RE = r'SCS\d{6}[A-Z]+.\d+'
VAR_ACCESSION_RE = r'SCSVAR\d{6}[A-Z]+.\d+.\d+'


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
    # TODO: Write this.
    pass


def valid_scoreset_score_data_input(string):
    from .forms import Constants

    fp = StringIO(string)
    expected_header = [Constants.HGVS_COLUMN]
    header = [l.strip() for l in fp.readline().strip().split(',')]
    try:
        valid_header = header[0] == expected_header[0]
        if not valid_header:
            raise ValueError()
    except:
        raise ValidationError(
            _(
                "Header requires the column 'hgvs'. Ensure the columns are "
                "separated by a comma, and that 'hgvs' is the first column."
            )
        )
    if len(list(fp.readlines())) < 1:
        raise ValidationError(_("Dataset cannot be empty."))


def valid_scoreset_count_data_input(string):
    from io import StringIO
    fp = StringIO(string)
    expected_header = [Constants.HGVS_COLUMN]
    header = [l.strip() for l in fp.readline().strip().split(',')]
    try:
        valid_header = (header[0] == expected_header[0])
        if not valid_header:
            raise ValueError()
    except:
        raise ValidationError(
            _(
                "Header requires the column 'hgvs'. Ensure the columns are "
                "separated by a comma, and that 'hgvs' is the first column."
            )
        )
    if len(list(fp.readlines())) < 1:
        raise ValidationError(_("Dataset cannot be empty."))


def valid_scoreset_json(json_object):
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
            _("Value for key %(key)s must not be empty."),
            params={"key": SCORES_KEY}
        )
    except ValidationError:
        type_ = type(json_object[SCORES_KEY][0]).__name__
        raise ValidationError(
            _("%(data)s list values must be strings not %(type)s."),
            params={"data": json_object[SCORES_KEY], "type": type_}
        )

    try:
        if not isinstance(json_object[COUNTS_KEY][0], str):
            raise ValidationError()
    except IndexError:
        raise ValidationError(
            _("Value for key %(key)s must not be empty."),
            params={"key": COUNTS_KEY}
        )
    except ValidationError:
        type_ = type(json_object[COUNTS_KEY][0]).__name__
        raise ValidationError(
            _("%(data)s list values must be strings not %(type)s."),
            params={"data": json_object[COUNTS_KEY], "type": type_}
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
