import io
import csv

from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from core.utilities import is_null

from . import constants

validate_csv_extension = FileExtensionValidator(allowed_extensions=['csv'])
validate_json_extension = FileExtensionValidator(allowed_extensions=['json'])


def read_header_from_io(file, label=None, msg=None):
    if label is None:
        label = 'Uploaded'
    try:
        header_line = file.readline()
        if isinstance(header_line, bytes):
            header_line = header_line.decode()
        file.seek(0)
        f = io.StringIO(header_line.strip())
        return [h.strip() for h in csv.DictReader(f, delimiter=',').fieldnames]
    except Exception:
        if not msg:
            msg = "A header could not be parsed from your {} file. Make sure" \
                  "Columns are comma delimited. Column names with commas must be" \
                  "escaped by enclosing them in double quotes.".format(label)
        raise ValidationError(msg)


def validate_has_hgvs_in_header(header, label=None, msg=None):
    if label is None:
        label = 'Uploaded'
    params = {}
    if msg is None:
        msg = (
            "Your %(label)s file must define either a nucleotide hgvs column "
            "'%(col_nt)s' or a protein hgvs column '%(col_p)s'. "
            "Columns are case-sensitive and must be comma delimited."
        )
        params = {
            'label': label,
            'col_nt': constants.hgvs_nt_column,
            'col_p': constants.hgvs_pro_column,
        }
    if not set(header) & set(constants.hgvs_columns):
        raise ValidationError(msg, params=params)


def validate_at_least_one_numeric_column(header, label=None, msg=None):
    if label is None:
        label = 'Uploaded'
    params = {}
    if not any(v not in constants.hgvs_columns for v in header):
        if msg is None:
            msg = "Your %(label)s file header must define at " \
                  "least one numeric column."
            params = {'label': label}
        raise ValidationError(msg, params=params)


def validate_header_contains_no_null_columns(header, label=None, msg=None):
    if label is None:
        label = 'uploaded'

    any_null = any([is_null(v) for v in header])
    if any_null:
        if msg is None:
            readable_null_values = set([
                x.lower().strip()
                for x in constants.nan_col_values if x.strip()
            ])
            msg = (
                "Header cannot contain blank/empty/whitespace only columns "
                "or the following case-insensitive null values: [{}].".format(
                    ', '.join(readable_null_values))
            )
        raise ValidationError(msg)
    
    
def validate_datasets_define_same_variants(scores, counts):
    vs_score = set([
        (v.get(constants.hgvs_nt_column, None),
         v.get(constants.hgvs_pro_column, None))
        for k, v in scores.items()
    ])
    
    vs_count = set([
        (v.get(constants.hgvs_nt_column, None),
         v.get(constants.hgvs_pro_column, None))
        for k, v in counts.items()
    ])
    if vs_score.difference(vs_count) or vs_count.difference(vs_score):
        raise ValidationError(
            "Your score and counts files do not define the same variants. "
            "Check that the hgvs columns in both files match."
        )


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
    file.seek(0)
    header = read_header_from_io(file, label='Score')
    validate_header_contains_no_null_columns(header, label='Score')
    validate_has_hgvs_in_header(header, label='Score')
    validate_at_least_one_numeric_column(header, label='Score')

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
    file.seek(0)
    header = read_header_from_io(file, label='Count')
    validate_header_contains_no_null_columns(header, label='Count')
    validate_has_hgvs_in_header(header, label='Count')
    validate_at_least_one_numeric_column(header, label='Count')


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
