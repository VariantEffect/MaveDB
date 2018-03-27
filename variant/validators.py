import csv
import re

from collections import defaultdict

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext

from dataset import constants as constants
from main.utils import is_null

# Matches a single amino acid substitution in HGVS_ format.
RE_PROTEIN = re.compile(
    "(?P<match>p\.(?P<pre>[A-Z][a-z][a-z])(?P<pos>-?\d+)"
    "(?P<post>[A-Z][a-z][a-z]))")

# Matches a single nucleotide substitution (coding or noncoding) in HGVS_ format.
RE_NUCLEOTIDE = re.compile(
    "(?P<match>[nc]\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")

# Matches a single coding nucleotide substitution in HGVS_ format.
RE_CODING = re.compile(
    "(?P<match>c\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]) "
    "\(p\.(?:=|[A-Z][a-z][a-z]-?\d+[A-Z][a-z][a-z])\))")

# Matches a single noncoding nucleotide substitution in HGVS_ format.
RE_NONCODING = re.compile(
    "(?P<match>n\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")


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
    file : :class:`io.TextIOWrapper`
        An open file handle in read mode.

    is_meta : bool, optional. Default: False
        If True, will not attempt to cast non-hgvs fields to a float.

    Returns
    -------
    `tuple`
        List of parsed header columns, and a dictionary mapping a hgvs string
        to a dictionary of column value pairs.
    """
    hgvs_col = constants.hgvs_column
    validate_hgvs = validate_hgvs_string
    hgvs_map = {}
    header = []
    order = defaultdict(lambda: 2)
    order[hgvs_col] = 0
    order[constants.required_score_column] = 1

    for i, row in enumerate(csv.DictReader(file)):
        # Get the header information. By this point, the other file validators
        # should have been run, so we are guaranteed the header is correct.
        if i == 0:
            header = list(sorted(row.keys(), key=lambda x: order[x]))
            hgvs_map = defaultdict(
                lambda: dict(**{c: None for c in header})
            )

        row = {
            k.strip(): None if is_null(v) else v.strip()
            for k, v in row.items()
        }
        if not isinstance(row[hgvs_col], str):
            raise ValidationError(
                (
                    "Type for column '%(col)s' at line %(i)s is '%(dtype)s'. "
                    "Expected 'str'."
                ),
                params={'col': hgvs_col, 'i': i,
                        'dtype': type(row[hgvs_col]).__name__}
            )

        # Validate hgvs string.
        validate_hgvs(row[constants.hgvs_column])
        hgvs_string = row[hgvs_col]

        # Ensure all values for columns other than 'hgvs' are either an int
        # or a float.
        for k, v in row.items():
            if k == constants.hgvs_column:
                continue
            if v is not None and not is_meta:
                try:
                    v = float(v)
                    row[k] = v
                except ValueError:
                    raise ValidationError(
                        (
                            "Type for column '%(col)s' at line %(i)s is "
                            "'%(dtype)s'. Expected either an 'int' or 'float'."
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

    return header, hgvs_map