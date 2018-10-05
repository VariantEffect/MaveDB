import csv
from hgvsp import is_multi

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext

from core.utilities import is_null

from dataset import constants as constants
from dataset.validators import (
    read_header_from_io,
    validate_at_least_one_numeric_column,
    validate_has_hgvs_in_header,
    validate_header_contains_no_null_columns
)

from variant import constants as hgvs_constants
from variant.validators.hgvs import (
    validate_multi_variant, validate_single_variant, infer_level, Level
)

sy_or_wt = (hgvs_constants.wildtype, hgvs_constants.synonymous)


def validate_scoreset_columns_match_variant(dataset_columns, variant_data):
    if sorted(dataset_columns[constants.score_columns]) != \
            sorted(list(variant_data[constants.variant_score_data].keys())):
        raise ValidationError(
            "Variant score columns do not match parent's columns.")
    if sorted(dataset_columns[constants.count_columns]) != \
            sorted(list(variant_data[constants.variant_count_data].keys())):
        raise ValidationError(
            "Variant count columns do not match parent's columns.")


def validate_hgvs_string(value, level=None):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    if not isinstance(value, str):
        raise ValidationError(
            "Variant HGVS values input must be strings. ",
            "'{}' has the type '{}'.".format(value, type(value).__name__)
        )
    if is_null(value):
        raise ValidationError(
            "HGVS values cannot be empty or one of '{}'.".format(
                ', '.join([v for v in constants.nan_col_values if v.strip()])
            ))
    if value in sy_or_wt:
        return
    if is_multi(value):
        validate_multi_variant(value, level=level)
    else:
        validate_single_variant(value, level=level)


def validate_variant_json(dict_):
    """
   Checks a given dictionary to ensure that it is suitable to be used
   as the `data` attribute in a :class:`Variant` instance.

   Parameters
   ----------
   dict_ : dict
       Dictionary of keys mapping to a list.
   """
    expected_keys = [
        constants.variant_score_data,
        constants.variant_count_data,
    ]
    for key in expected_keys:
        if key not in dict_.keys():
            raise ValidationError(
                ugettext("Missing the required key '%(key)'."),
                params={"data": dict_, "key": key}
            )

    if constants.required_score_column not in \
            dict_[constants.variant_score_data]:
        raise ValidationError(
            "Missing required column '%(col)s' in variant's score data.",
            params={'col': constants.required_score_column}
        )

    extras = [k for k in dict_.keys() if k not in set(expected_keys)]
    if len(extras) > 0:
        extras = [k for k in dict_.keys() if k not in expected_keys]
        raise ValidationError(
            ugettext("Encountered unexpected keys '%(extras)s'."),
            params={"extras": extras}
        )

    # Check the correct data types are given.
    for key in expected_keys:
        if not isinstance(dict_[key], dict):
            type_ = type(dict_[key]).__name__
            raise ValidationError(
                ugettext("Value for '%(key)' must be a dict not %(type)s."),
                params={"key": key, "type": type_}
            )


def validate_variant_rows(file):
    """
    Variant data validator that checks the following:

        1) Datatypes of rows must be either int, float or NoneType
        2) HGVS string is a valid hgvs string,
        3) Hgvs does not appear more than once in rows

    Variant strings must be `double-quoted` to ignore splitting multi-mutants
    on commas.

    Parameters
    ----------
    file : `io.FileIO` or `io.BytesIO` or `io.StringIO`
        An open file handle in read mode.

    Returns
    -------
    `tuple`
        List of parsed header columns, and a dictionary mapping a hgvs string
        to a dictionary of column value pairs.
    """
    from ..models import column_order

    validate_hgvs = validate_hgvs_string

    # Read header, validate and iterate one line since `read_header_from_io`
    # seeks back to the start.
    header = read_header_from_io(file)
    validate_has_hgvs_in_header(header)
    validate_at_least_one_numeric_column(header)
    validate_header_contains_no_null_columns(header)
    file.readline()  # remove header line

    # csv reader requires strings and the file is opened in bytes mode by
    # default by the django form.
    lines = (
        line.decode('utf-8') if isinstance(line, bytes) else line
        for line in file.readlines()
    )
    hgvs_map = defaultdict(lambda: dict(**{c: None for c in header}))

    # Determine which is the primary hgvs column. Defaults to _nt. _p is only
    # selected when _nt is not provided.
    defines_nt_hgvs = constants.hgvs_nt_column in header
    defines_p_hgvs = constants.hgvs_pro_column in header
    if defines_nt_hgvs and defines_p_hgvs:
        primary_hgvs_column = constants.hgvs_nt_column
    elif defines_p_hgvs and not defines_nt_hgvs:
        primary_hgvs_column = constants.hgvs_pro_column
    else:
        primary_hgvs_column = constants.hgvs_nt_column

    for i, row in enumerate(csv.DictReader(lines, fieldnames=header)):
        # Check to see if the columns have been parsed correctly. Parsing will
        # break if a user does not double-quote string values containing
        # commas.
        if sorted([str(x) for x in row.keys()]) != sorted(header):
            raise ValidationError(
                (
                    "Row columns '%(row)s' do not match those found in the "
                    "header '%(header)s. Check that row values "
                    "containing commas are double quoted and the number of row "
                    "columns matches the number of columns defined by the file "
                    "header."
                ),
                params={'row': list(row.keys()), 'header': header}
            )

        # White-space strip and convert null values to None
        row = {
            k.strip(): None if is_null(v) else v.strip()
            for k, v in row.items()
        }

        # Check that each hgvs_nt and hgvs_p have the syntax for the
        # appropriate hgvs level.
        hgvs_nt = row.get(constants.hgvs_nt_column, None)
        hgvs_p = row.get(constants.hgvs_pro_column, None)
        if not is_null(hgvs_nt):
            level = infer_level(hgvs_nt)
            if hgvs_nt not in sy_or_wt and level not in [Level.DNA, Level.RNA]:
                raise ValidationError(
                    message=(
                        "Column '%(col)s' only supports DNA/RNA HGVS syntax."),
                    params={'col': constants.hgvs_nt_column}
                )
            validate_hgvs(hgvs_nt)
        else:
            hgvs_nt = None

        if not is_null(hgvs_p):
            level = infer_level(hgvs_p)
            if hgvs_p not in sy_or_wt and level != Level.PROTEIN:
                raise ValidationError(
                    message=(
                        "Column '%(col)s' only supports Protein HGVS syntax."),
                    params={'col': constants.hgvs_pro_column}
                )
            validate_hgvs(hgvs_p)
        else:
            hgvs_p = None

        # The primary hgvs column defaults to _nt. It is only _p when
        # the only hgvs column defined is the protein hgvs column.
        if defines_nt_hgvs and defines_p_hgvs:
            primary_hgvs = hgvs_nt
        elif defines_p_hgvs and not defines_nt_hgvs:
            primary_hgvs = hgvs_p
        else:
            primary_hgvs = hgvs_nt

        if primary_hgvs is None:
            raise ValidationError(
                "Row %(i)s is missing the HGVS string for column '%(col)s'.",
                params={'col': primary_hgvs_column, 'i': i + 1}
            )

        # Ensure all values for columns other than 'hgvs' are either an int,
        # float or None
        for k, v in row.items():
            if k in constants.hgvs_columns:
                continue
            if v is not None:
                try:
                    v = float(v)
                    row[k] = v
                except ValueError:
                    raise ValidationError(
                        (
                            "The type for column '%(col)s' at line %(i)s is "
                            "'%(dtype)s'. Non-HGVS columns must be either "
                            "an integer or floating point number."
                        ),
                        params={'col': k, 'i': i + 1,
                                'dtype': type(v).__name__}
                    )

        # Make sure the variant has been defined more than one time.
        if primary_hgvs in hgvs_map:
            raise ValidationError(
                "Variant '%(hgvs)s' has been re-defined at index %(i)s. Input "
                "cannot contain the same variant twice in different rows.",
                params={'hgvs': primary_hgvs, 'i': i + 1}
            )
        else:
            # Users may upload a dataset without only one of the hgvs columns.
            # Add both in even if the values are None so less checking will
            # need to be done by the forms.
            row[constants.hgvs_nt_column] = hgvs_nt
            row[constants.hgvs_pro_column] = hgvs_p
            hgvs_map[primary_hgvs] = row

    if not len(header) or not len(hgvs_map):
        raise ValidationError(
            "No variants could be parsed from your input file. Please upload "
            "a non-empty file.")

    # Sort header and remove hgvs cols since the hgvs strings are the map keys.
    header = [v for v in header if v not in constants.hgvs_columns]
    header = list(sorted(header, key=lambda x: column_order[x]))
    return header, primary_hgvs_column, hgvs_map
