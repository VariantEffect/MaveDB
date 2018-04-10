from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from dataset import constants as constants
from core.utilities import is_null

validate_csv_extension = FileExtensionValidator(allowed_extensions=['csv'])


def read_header_from_io(file, label=None, msg=None):
    params = {}
    try:
        header_line = file.readline()
        if isinstance(header_line, bytes):
            header_line = header_line.decode()
        file.seek(0)
        return [l.strip() for l in header_line.strip().split(',')]
    except Exception as e:
        if msg is None:
            msg = (
                "Encountered an error while reading %(label)s file header: "
                "%(reason)s."
            )
            params = {'reason': str(e), 'label': label}
        raise ValidationError(msg, params=params)


def validate_has_hgvs_in_header(header, label=None, msg=None):
    params = {}
    if msg is None:
        msg = (
            "%(label)s file is missing the required column '%(col)s'. "
            "Columns are case-sensitive and must be comma delimited."
        )
        params = {'label': label, 'col': constants.hgvs_column}
    if constants.hgvs_column not in header:
        raise ValidationError(msg, params=params)


def validate_at_least_two_columns(header, label=None, msg=None):
    params = {}
    if msg is None:
        msg = "%(label)s file header must have at least 2 columns."
        params = {'label': label}
    if len(header) < 2:
        raise ValidationError(msg, params=params)


def validate_header_contains_no_null_columns(header, label=None, msg=None):
    params = {}
    for i, value in enumerate(header):
        if is_null(value):
            if msg is None:
                msg = (
                    "The header of your %(label)s file cannot contain "
                    "null values. Found null value '%(value)s' at "
                    "position %(i)s."
                )
                params = {'value': value, 'i': i, 'label': label}
            raise ValidationError(msg, params)


def validate_scoreset_score_data_input(file):
    """
    Validator function for checking that the scores file input contains
    at least the column 'hgvs' and 'score'. Returns the file to position 0
    after reading the header (first line).

    Parameters
    ----------
    file : :class:`io.FileIO`
        An open file handle in read mode.
    """
    header = read_header_from_io(file, label='Score')
    validate_header_contains_no_null_columns(header, label='Score')
    validate_has_hgvs_in_header(header, label='Score')
    validate_at_least_two_columns(header, label='Score')

    if constants.required_score_column not in header:
        raise ValidationError(
            ugettext(
                "Score data file is missing the required column '%(col)s'. "
                "Columns are case-sensitive and must be comma delimited."
            ),
            params={'col': constants.required_score_column}
        )


def validate_scoreset_count_data_input(file):
    """
    Validator function for checking that the counts file input contains
    at least the column 'hgvs'. Returns the file to position 0
    after reading the header (first line).

    Parameters
    ----------
    file : :class:`io.FileIO`
        File parsed by a `django` form.
    """
    header = read_header_from_io(file, label='Count')
    validate_header_contains_no_null_columns(header, label='Count')
    validate_has_hgvs_in_header(header, label='Count')
    validate_at_least_two_columns(header, label='Count')


def validate_scoreset_meta_data_input(file):
    """
    Validator function for checking that the `meta` file input contains
    at least the column 'hgvs'. Returns the file to position 0
    after reading the header (first line).

    Parameters
    ----------
    file : :class:`io.FileIO`
        File parsed by a `django` form.
    """
    header = read_header_from_io(file, label='Metadata')
    validate_header_contains_no_null_columns(header, label='Metadata')
    validate_has_hgvs_in_header(header, label='Metadata')
    validate_at_least_two_columns(header, label='Metadata')


def validate_scoreset_json(dict_):
    """
    Checks a given dictionary to ensure that it is suitable to be used
    as the `dataset_columns` attribute in a :class:`ScoreSet` instance.

    Parameters
    ----------
    dict_ : dict
        Dictionary of keys mapping to a list.
    """
    required_columns = [
        constants.score_columns,
        constants.count_columns,
        constants.metadata_columns
    ]

    for key in required_columns:
        if key not in dict_.keys():
            raise ValidationError(
                ugettext("Scoreset data is missing the required key "
                         "'%(key)s'."),
                params={"key": key}
            )

        columns = dict_[key]
        if not all([isinstance(c, str) for c in columns]):
            raise ValidationError(ugettext("Header values must be strings."))

        if not isinstance(columns, list):
            type_ = type(columns).__name__
            raise ValidationError(
                ugettext("Value for %(key)s must be a list not %(type)s."),
                params={"key": key.replace('_', ' '), "type": type_}
            )

        # Check score columns is not-empty and at least contains hgvs and score
        if key == constants.score_columns:
            if not columns:
                raise ValidationError(
                    ugettext(
                        "Missing required columns '%(col1)s' and '%(col2)s' "
                        "for score dataset."),
                    params={
                        "col1": constants.hgvs_column,
                        "col2": constants.required_score_column
                    })
            if constants.required_score_column not in columns:
                raise ValidationError(
                    ugettext(
                        "Missing required column '%(col)s' for "
                        "score dataset."),
                    params={"col": constants.required_score_column}
                )

    # Check there are not unexptected columns supplied to the scoreset json
    # field.
    extras = [k for k in dict_.keys() if k not in set(required_columns)]
    if len(extras) > 0:
        extras = [k for k in dict_.keys() if k not in required_columns]
        raise ValidationError(
            ugettext("Encountered unexpected keys '%(extras)s'."),
            params={"extras": extras}
        )
