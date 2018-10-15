import re
import numpy as np
import pandas as pd
from hgvsp import is_multi

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext

from core.utilities import is_null

from dataset import constants
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
            "Variant HGVS values input must be strings. "
            "'{}' has the type '{}'.".format(value, type(value).__name__)
        )
    if not value or null_values_re.fullmatch(value.lower()):
        return None
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


def validate_columns_are_numeric(df):
    """Checks non-hgvs columns for float or int data."""
    for column in df.columns:
        if column in [constants.hgvs_pro_column, constants.hgvs_nt_column]:
            continue
        else:
            if not (np.issubdtype(df.dtypes[column], np.floating) or
                    np.issubdtype(df.dtypes[column], np.integer)):
                raise ValidationError(
                    "Expected only float or int data columns. Got {}.".format(
                        str(df.dtypes[column])
                    ))


def validate_has_column(df, column):
    """Validates that a `DataFrame` contains `column` in it's columns."""
    if column not in df.columns:
        raise ValidationError(
            "Missing column '{}'. Parsed columns {}.".format(
                column, ', '.join(df.columns)
            )
        )


def validate_hgvs_nt_uniqueness(df):
    """Validate that hgvs columns only define a variant once."""
    dups = df.loc[:, constants.hgvs_nt_column].duplicated(keep=False)
    if np.any(dups):
        dup_list = ["{} ({})".format(x, y) for x, y in
                    zip(df.loc[dups, constants.hgvs_nt_column],
                        dups.index[dups])]
        raise ValidationError(
            "duplicate HGVS nucleotide strings found: {}".format(
                ', '.join(sorted(dup_list))
            ))


def validate_hgvs_pro_uniqueness(df):
    """Validate that hgvs columns only define a variant once."""
    dups = df.loc[:, constants.hgvs_pro_column].duplicated(keep=False)
    if np.any(dups):
        dup_list = ["{} ({})".format(x, y) for x, y in
                    zip(df.loc[dups, constants.hgvs_pro_column],
                        dups.index[dups])]
        raise ValidationError(
            "Duplicate HGVS protein strings found: {}".format(
                ', '.join(sorted(dup_list))
            ))


null_values = ('nan', 'na', 'none', '', 'undefined', 'n/a')
null_values_re = re.compile(r'\s+|none|nan|na|undefined|n/a|null')


def variant_is_null(variant):
    """Returns `True` if `variant` is None, Na, NaN or empty."""
    return (not variant) or \
           str(variant).strip().lower() in null_values


def format_column(values, astype=float):
    """
    Formats a list of numeric values by replacing null values with
    `np.NaN` and casting to `astype`.

    Parameters
    ----------
    values : list[Union[float, int]]
        List of values to format.

    astype : callable, optional
        Type-casting callback accepting a single argument.

    Returns
    -------
    list[Any]
        List of values with type returned by `astype` and null values
        replaced with `np.NaN`.
    """
    if astype == str:
        nan_val = None
    else:
        nan_val = np.NaN
    return [
        nan_val if null_values_re.fullmatch(str(v).lower()) else astype(v)
        for v in values
    ]


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

    # Load file in a dataframe for quicker processing.
    df = pd.read_csv(file, encoding='utf-8', quotechar='\"')
    if not len(df):
        raise ValidationError(
            "No variants could be parsed from your input file. Please upload "
            "a non-empty file.")

    # Formats the data in each column replacing null values with np.NaN
    for column in df.columns:
        try:
            if column in constants.hgvs_columns:
                df[column] = format_column(df[column], astype=str)
            else:
                df[column] = format_column(df[column], astype=float)
        except ValueError as e:
            raise ValidationError(str(e).capitalize())

    # Determine which is the primary hgvs column. Defaults to _nt. _pro is only
    # selected when _nt is not provided.
    defines_nt_hgvs = constants.hgvs_nt_column in df.columns
    defines_p_hgvs = constants.hgvs_pro_column in df.columns
    if defines_nt_hgvs and defines_p_hgvs:
        primary_hgvs_column = constants.hgvs_nt_column
    elif defines_p_hgvs and not defines_nt_hgvs:
        primary_hgvs_column = constants.hgvs_pro_column
    else:
        primary_hgvs_column = constants.hgvs_nt_column

    # Check that the primary column is fully specified.
    null_primary = df.loc[:, primary_hgvs_column].apply(variant_is_null)
    if any(null_primary):
        raise ValidationError(
            "Primary column (inferred as '{}') cannot "
            "contain any null values from '{}' (case-insensitive).".format(
                primary_hgvs_column, ', '.join(null_values)
            ))

    # Check that the hgvs_nt column does not have duplicate rows.
    if primary_hgvs_column == constants.hgvs_nt_column:
        validate_hgvs_nt_uniqueness(df)

    # Validate variants where applicable
    if defines_nt_hgvs:
        df.loc[:, constants.hgvs_nt_column].apply(validate_hgvs)
    if defines_p_hgvs:
        df.loc[:, constants.hgvs_pro_column].apply(validate_hgvs)

    # Finally validate all other columns are numeric.
    validate_columns_are_numeric(df)

    # Sort header and remove hgvs cols since the hgvs strings are the map keys.
    header = [v for v in df.columns if v in constants.hgvs_columns]
    header += list(sorted(
        [v for v in df.columns if v not in constants.hgvs_columns],
        key=lambda x: column_order[x]))
    df = df[header]

    hgvs_map = defaultdict(lambda: dict(**{c: None for c in header}))
    for i, row in df.iterrows():
        data = row.to_dict()
        data[constants.hgvs_nt_column] = data.get(
            constants.hgvs_nt_column, None
        )
        data[constants.hgvs_pro_column] = data.get(
            constants.hgvs_pro_column, None
        )
        hgvs_map[row[primary_hgvs_column]] = data

    # Remove hgvs columns from header. Form validator expects only
    # additional non-hgvs in the returned header.
    header = [v for v in df.columns if v not in constants.hgvs_columns]
    return header, primary_hgvs_column, hgvs_map
