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

from main.utils import is_null

# Matches a single amino acid substitution in HGVS_ format.
RE_PROTEIN = re.compile(
    "(?P<match>p\.(?P<pre>[A-Z][a-z][a-z])(?P<pos>-?\d+)"
    "(?P<post>[A-Z][a-z][a-z]))")

# Matches a single nucleotide substitution (coding or noncoding) in
# HGVS_ format.
RE_NUCLEOTIDE = re.compile(
    "(?P<match>[nc]\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")

# Matches a single coding nucleotide substitution in HGVS_ format.
RE_CODING = re.compile(
    "(?P<match>c\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]) "
    "\(p\.(?:=|[A-Z][a-z][a-z]-?\d+[A-Z][a-z][a-z])\))")

# Matches a single noncoding nucleotide substitution in HGVS_ format.
RE_NONCODING = re.compile(
    "(?P<match>n\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")


def validate_scoreset_columns_match_variant(scoreset, variant):
    if sorted(scoreset.score_columns) != sorted(variant.score_columns):
        raise ValidationError(
            "Variant score columns do not match parent's columns.")
    if sorted(scoreset.count_columns) != sorted(variant.count_columns):
        raise ValidationError(
            "Variant count columns do not match parent's columns.")
    if sorted(scoreset.metadata_columns) != sorted(variant.metadata_columns):
        raise ValidationError(
            "Variant metadata columns do not match parent's columns.")


def validate_hgvs_string(value):
    return
    # variants = [v.strip() for v in string.strip().split(',')]
    #
    # protein_matches = all([RE_PROTEIN.match(v) for v in variants])
    # nucleotide_matches = all([re_nucleotide.match(v) for v in variants])
    # coding_matches = all([re_coding.match(v) for v in variants])
    # noncoding_matches = all([re_noncoding.match(v) for v in variants])
    # wt_or_sy = all([v in ["_wt", "_sy"] for v in variants])
    #
    # if not (protein_matches or nucleotide_matches or
    #         coding_matches or noncoding_matches or wt_or_sy):
    #     raise ValidationError(
    #         ugettext("Variant '%(variant)s' is not a valid HGVS string."),
    #         params={'variant': string}
    #     )


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
        constants.variant_metadata
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


def validate_variant_rows(file, is_meta=False):
    """
    Variant data validator that checks the following:

        1) Datatypes of rows must be either str, int, float or NoneType if
           `is_meta` is False.
        2) HGVS string is a valid hgvs string,
        3) Hgvs does not appear more than once in rows

    Variant strings must be `double-quoted` to ignore splitting multi-mutants
    on commas.

    Parameters
    ----------
    file : :class:`io.FileIO`
        An open file handle in read mode.

    is_meta : bool, optional. Default: False
        If True, will not attempt to cast non-hgvs fields to a float.

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
    header = read_header_from_io(file)
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
            "following case-insensitive null values: {}."
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
                    "Check that multi-mutants and metadata columns/values "
                    "containing commas are double quoted."
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
                    "Missing required column '%(col)s' in line %(i)s."
                ),
                params={'col': hgvs_col, 'i': i}
            )
        hgvs_string = row.pop(constants.hgvs_column)
        validate_hgvs(hgvs_string)
        if not isinstance(hgvs_string, str):
            raise ValidationError(
                (
                    "Type for column '%(col)s' at line %(i)s is '%(dtype)s'. "
                    "Expected 'str'. HGVS values must be strings only."
                ),
                params={'col': hgvs_col, 'i': i,
                        'dtype': type(hgvs_string).__name__}
            )

        # Ensure all values for columns other than 'hgvs' are either an int
        # or a float if the input is not a metadata file.
        if not is_meta:
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
                           params={'col': k, 'i': i, 'dtype': type(v).__name__}
                        )

        # Make sure the variant has been defined more than one time.
        if hgvs_string in hgvs_map:
            raise ValidationError(
                "Variant '%(hgvs)s' has been re-defined at index %(i)s. Input "
                "cannot contain the same variant twice in different rows.",
                params={'hgvs': hgvs_string, 'i': i}
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

