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
    # TODO: Write this.
    pass


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

    for key, value in json_object[SCORES_KEY].items():
        if not isinstance(value, list):
            raise ValidationError(
                _("data for %(key)s must be a list not %(type)s."),
                params={"key": key, "type": type(value).__name__}
            )
        if len(value) != 1:
            raise ValidationError(
                _("data %(data)s for %(key)s must have exactly one item."),
                params={"key": key, "data": value}
            )

    for key, value in json_object[COUNTS_KEY].items():
        if not isinstance(value, list):
            raise ValidationError(
                _("data for %(key)s must be a list not %(type)s."),
                params={"key": key, "type": type(value).__name__}
            )
        if len(value) != 1:
            raise ValidationError(
                _("data %(data)s for %(key)s must have exactly one item."),
                params={"key": key, "data": value}
            )
