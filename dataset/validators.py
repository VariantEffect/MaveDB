from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

import dataset.constants as constants

# --------------------------------------------------------------------------- #
#                     ScoreSet/Variant json Validators
# --------------------------------------------------------------------------- #
validate_csv_extension = FileExtensionValidator(allowed_extensions=['csv'])

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
    header_line = file.readline()
    if isinstance(header_line, bytes):
        header_line = header_line.decode()

    header = [l.strip() for l in header_line.strip().split(',')]
    if constants.hgvs_column not in header:
        raise ValidationError(
            ugettext(
                "Score data file is missing the required column '%(col). "
                "Columns are case-sensitive and must be comma delimited."
            ),
            params={'col': constants.hgvs_column}
        )
    if constants.required_score_column not in header:
        raise ValidationError(
            ugettext(
                "Score data file is missing the required column '%(col). "
                "Columns are case-sensitive and must be comma delimited."
            ),
            params={'col': constants.required_score_column}
        )
    file.seek(0)


def validate_scoreset_count_data_input(file):
    """
    Validator function for checking that the counts file input contains
    at least the column 'hgvs'. Returns the file to position 0
    after reading the header (first line).

    Parameters
    ----------
    file : :class:`File`
        File parsed by a `django` form.
    """
    header_line = file.readline()
    if isinstance(header_line, bytes):
        header_line = header_line.decode()

    header = [l.strip() for l in header_line.strip().split(',')]
    if constants.hgvs_column not in header:
        raise ValidationError(
            ugettext(
                "Count data file is missing the required column '%(col). "
                "Columns are case-sensitive and must be comma delimited."
            ),
            params={'col': constants.hgvs_column}
        )

    if len(header) < 2:
        raise ValidationError(
            ugettext("Count file header must have at least 2 columns.")
        )
    file.seek(0)


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
                ugettext("Scoreset data is missing the required key '%(key)s'."),
                params={"key": key}
            )

        elif not isinstance(dict_[key], list):
            type_ = type(dict_[constants.score_columns]).__name__
            raise ValidationError(
                ugettext("Value for '%(key)' must be a list not %(type)s."),
                params={"key": key, "type": type_}
            )

        elif len(dict_[key]) == 0 and key == constants.score_columns:
            raise ValidationError(
                ugettext("No header could be found for '%(key)s' dataset."),
                params={"key": key}
            )

        elif not all([isinstance(c, str) for c in dict_[key]]):
            raise ValidationError(ugettext("Header values must be strings."))


    extras = [k for k in dict_.keys() if k not in set(required_columns)]
    if len(extras) > 0:
        extras = [k for k in dict_.keys() if k not in required_columns]
        raise ValidationError(
            ugettext("Encountered unexpected keys '%(extras)s'."),
            params={"extras": extras}
        )
