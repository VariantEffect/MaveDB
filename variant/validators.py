import csv
import re

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext

from dataset import constants as constants
from dataset.validators import (
    read_header_from_io,
    validate_at_least_two_columns,
    validate_has_hgvs_in_header,
    validate_header_contains_no_null_columns
)

from core.utilities import is_null

from variant.hgvs import (
    is_multi, validate_multi_variant, validate_single_variants
)


def validate_scoreset_columns_match_variant(dataset_columns, variant_data):
    if sorted(dataset_columns[constants.score_columns]) != \
            sorted(list(variant_data[constants.variant_score_data].keys())):
        raise ValidationError(
            "Variant score columns do not match parent's columns.")
    if sorted(dataset_columns[constants.count_columns]) != \
            sorted(list(variant_data[constants.variant_count_data].keys())):
        raise ValidationError(
            "Variant count columns do not match parent's columns.")


def validate_hgvs_string(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    if not isinstance(value, str):
        raise ValidationError(
            "Variant HGVS values input must be strings. ",
            "Found '{}'.".format(type(value).__name__)
        )
    if is_multi(value):
        validate_multi_variant(value)
    else:
        validate_single_variants(value)


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
    file : `io.FileIO` or `io.BytesIO`
        An open file handle in read mode.

    Returns
    -------
    `tuple`
        List of parsed header columns, and a dictionary mapping a hgvs string
        to a dictionary of column value pairs.
    """
    readable_null_values = set(
        x.lower().strip() for x in constants.nan_col_values if x.strip())
    hgvs_col = constants.hgvs_column
    validate_hgvs = validate_hgvs_string

    # 'score' should be the first column in a score dataset
    order = defaultdict(lambda: 1)
    order[constants.required_score_column] = 0

    # Read header, validate and iterate one line since `read_header_from_io`
    # seeks back to the start.
    header = read_header_from_io(file, label='input')
    validate_has_hgvs_in_header(
        header,
        msg=(
            "Header is missing the required column '{}'. "
            "Note that column names are case-sensitive."
        ).format(hgvs_col))
    validate_at_least_two_columns(
        header,
        msg=(
            "Header requires at least two columns. Found {} column '{}'."
        ).format(len(header), ', '.join(header)))
    validate_header_contains_no_null_columns(
        header,
        msg=(
            "Header cannot contain blank/empty/whitespace only columns or the "
            "following case-insensitive null values: [{}]."
        ).format(', '.join(readable_null_values)))
    file.readline()  # remove header line

    # csv reader requires strings and the file is opened in bytes mode by
    # default by the django form.
    lines = (
        line.decode('utf-8') if isinstance(line, bytes) else line
        for line in file.readlines()
    )
    hgvs_map = defaultdict(lambda: dict(**{c: None for c in header}))

    for i, row in enumerate(csv.DictReader(lines, fieldnames=header)):
        # Check to see if the columns have been parsed correctly. Parsing will
        # break if a user does not double-quote string values containing
        # commas.
        if sorted([str(x) for x in row.keys()]) != sorted(header):
            raise ValidationError(
                (
                    "Row columns '%(row)s' do not match those found in the "
                    "header '%(header)s. "
                    "Check that multi-mutants and columns/values "
                    "containing commas are double quoted and that rows columns"
                    " match those in the header."
                ),
                params={'row': list(row.keys()), 'header': header}
            )

        # White-space strip and convert null values to None
        row = {
            k.strip(): None if is_null(v) else v.strip()
            for k, v in row.items()
        }

        # Remove the hgvs string from the row and validate it.
        if hgvs_col not in row:
            raise ValidationError(
                (
                    "Missing required column '%(col)s' in row %(i)s."
                ),
                params={'col': hgvs_col, 'i': i+1}
            )
        hgvs_string = row.pop(constants.hgvs_column)
        validate_hgvs(hgvs_string)
        if not isinstance(hgvs_string, str):
            raise ValidationError(
                (
                    "Type for column '%(col)s' at line %(i)s is '%(dtype)s'. "
                    "Expected 'str'. HGVS values must be strings only."
                ),
                params={'col': hgvs_col, 'i': i+1,
                        'dtype': type(hgvs_string).__name__}
            )

        # Ensure all values for columns other than 'hgvs' are either an int,
        # float or None
        for k, v in row.items():
            if k == constants.hgvs_column:
                continue
            if v is not None:
                try:
                    v = float(v)
                    row[k] = v
                except ValueError:
                    raise ValidationError(
                       (
                            "Type for column '%(col)s' at line %(i)s is "
                            "'%(dtype)s'. Expected either an 'int' or "
                            "'float'. Score/count uploads can only "
                            "contain numeric column values."
                       ),
                       params={
                           'col': k, 'i': i+1, 'dtype': type(v).__name__}
                    )

        # Make sure the variant has been defined more than one time.
        if hgvs_string in hgvs_map:
            raise ValidationError(
                "Variant '%(hgvs)s' has been re-defined at index %(i)s. Input "
                "cannot contain the same variant twice in different rows.",
                params={'hgvs': hgvs_string, 'i': i+1}
            )
        else:
            hgvs_map[hgvs_string] = row

    if not len(header) or not len(hgvs_map):
        raise ValidationError(
            "No variants could be parsed from your input file. Please upload "
            "a non-empty file.")

    # Sort header and remove 'hgvs' since the hgvs strings are the map keys.
    header.remove(hgvs_col)
    header = list(sorted(header, key=lambda x: order[x]))
    return header, hgvs_map
