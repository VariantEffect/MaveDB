
import csv
import re
from collections import defaultdict

from django.utils.translation import ugettext
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from main.utils import is_null
import experiment.constants as constants

DNA_SEQ_PATTERN = r'[ATGCatgc]+'

MAVEDB_EXPERIMENTSET_URN_DIGITS = 8
MAVEDB_URN_MAX_LENGTH = 64
MAVEDB_URN_NAMESPACE = "mavedb"

MAVEDB_EXPERIMENTSET_URN_PATTERN = r'^urn:{namespace}:\d{{{width}}}$'.format(
    namespace=MAVEDB_URN_NAMESPACE,
    width=MAVEDB_EXPERIMENTSET_URN_DIGITS
)
MAVEDB_EXPERIMENTSET_URN_RE = re.compile(MAVEDB_EXPERIMENTSET_URN_PATTERN)

MAVEDB_EXPERIMENT_URN_PATTERN = r'{pattern}-[a-z]+$'.format(
    pattern=MAVEDB_EXPERIMENTSET_URN_PATTERN[:-1]
)
MAVEDB_EXPERIMENT_URN_RE = re.compile(MAVEDB_EXPERIMENT_URN_PATTERN)

MAVEDB_SCORESET_URN_PATTERN = r'{pattern}-\d+$'.format(
    pattern=MAVEDB_EXPERIMENT_URN_PATTERN[:-1]
)
MAVEDB_SCORESET_URN_RE = re.compile(MAVEDB_SCORESET_URN_PATTERN)

MAVEDB_VARIANT_URN_PATTERN = r'{pattern}#\d+$'.format(
    pattern=MAVEDB_SCORESET_URN_PATTERN[:-1]
)
MAVEDB_VARIANT_URN_RE = re.compile(MAVEDB_VARIANT_URN_PATTERN)

MAVEDB_ANY_URN_PATTERN = '|'.join([r'({pattern})'.format(pattern=p) for p in (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN,
    MAVEDB_VARIANT_URN_PATTERN)
])
MAVEDB_ANY_URN_RE = re.compile(MAVEDB_ANY_URN_PATTERN)

SRA_BIOPROJECT_PATTERN = r'^PRJNA\d+$'
SRA_BIOPROJECT_RE = re.compile(SRA_BIOPROJECT_PATTERN)
SRA_STUDY_PATTERN = r'^[SED]RP\d+$'
SRA_STUDY_RE = re.compile(SRA_STUDY_PATTERN)
SRA_EXPERIMENT_PATTERN = r'^[SED]RX\d+$'
SRA_EXPERIMENT_RE = re.compile(SRA_EXPERIMENT_PATTERN)
SRA_RUN_PATTERN = r'^[SED]RR\d+$'
SRA_RUN_RE = re.compile(SRA_RUN_PATTERN)
SRA_ANY_PATTERN = '|'.join([r'({pattern})'.format(pattern=p) for p in (
    SRA_BIOPROJECT_PATTERN,
    SRA_STUDY_PATTERN,
    SRA_EXPERIMENT_PATTERN,
    SRA_RUN_PATTERN)
])
SRA_ANY_RE = re.compile(SRA_ANY_PATTERN)

#: Matches a single amino acid substitution in HGVS_ format.
RE_PROTEIN = re.compile(
    "(?P<match>p\.(?P<pre>[A-Z][a-z][a-z])(?P<pos>-?\d+)"
    "(?P<post>[A-Z][a-z][a-z]))")


#: Matches a single nucleotide substitution (coding or noncoding)
#: in HGVS_ format.
RE_NUCLEOTIDE = re.compile(
    "(?P<match>[nc]\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")


#: Matches a single coding nucleotide substitution in HGVS_ format.
RE_CODING = re.compile(
    "(?P<match>c\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]) "
    "\(p\.(?:=|[A-Z][a-z][a-z]-?\d+[A-Z][a-z][a-z])\))")


#: Matches a single noncoding nucleotide substitution in HGVS_ format.
RE_NONCODING = re.compile(
    "(?P<match>n\.(?P<pos>-?\d+)(?P<pre>[ACGT])>(?P<post>[ACGT]))")

# --------------------------------------------------------------------------- #
#                           URN Validators
# --------------------------------------------------------------------------- #
def validate_mavedb_urn(urn):
    if not MAVEDB_ANY_URN_RE.match(urn):
        raise ValidationError(
            "%(urn)s is not a valid urn.",
            params={"urn": urn}
        )


def validate_mavedb_urn_experimentset(urn):
    if not MAVEDB_EXPERIMENTSET_URN_RE.match(urn):
        raise ValidationError(
            "%(urn)s is not a valid Experiment Set urn.",
            params={"urn": urn}
        )


def validate_mavedb_urn_experiment(urn):
    if not MAVEDB_EXPERIMENT_URN_RE.match(urn):
        raise ValidationError(
            "%(urn)s is not a valid Experiment urn.",
            params={"urn": urn}
        )


def validate_mavedb_urn_scoreset(urn):
    if not MAVEDB_SCORESET_URN_RE.match(urn):
        raise ValidationError(
            "%(urn)s is not a valid Score Set urn.",
            params={"urn": urn}
        )


def validate_mavedb_urn_variant(urn):
    if not MAVEDB_VARIANT_URN_RE.match(urn):
        raise ValidationError(
            "%(urn)s is not a valid Variant urn.",
            params={"urn": urn}
        )


# --------------------------------------------------------------------------- #
#                           Sequence/HGVS Validators
# --------------------------------------------------------------------------- #
def validate_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_PATTERN, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )


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

# --------------------------------------------------------------------------- #
#                           ExternalIdentifier Validators
# --------------------------------------------------------------------------- #
def validate_sra_identifier(identifier):
    if not SRA_ANY_RE.match(identifier):
        raise ValidationError(
            "%(id)s is not a valid SRA identifier.",
            params={"id": identifier}
        )

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

        elif len(dict_[key]) == 0:
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
    hgvs_col = constants.hgvs_column
    validate_hgvs = validate_hgvs_string
    hgvs_json_map = None
    header = None
    order = defaultdict(lambda: 2)
    order[hgvs_col] = 0
    order[constants.required_score_column] = 1

    for i, row in enumerate(csv.DictReader(file)):
        # Get the header information. By this point, the other file validators
        # should have been run, so we are guaranteed the header is correct.
        if i == 0:
            header = list(sorted(row.keys(), key=lambda x: order[x]))
            hgvs_json_map = defaultdict(
                lambda: dict(**{c: None for c in header})
            )

        row = {
            k.strip(): None if is_null(v) else v.strip() for k, v in row.items()
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
        if hgvs_string in hgvs_json_map:
            raise ValidationError(
                "Variant '%(hgvs)s' has been re-defined at index %(i)s. Input "
                "cannot contain the same variant twice in different rows.",
                params={'hgvs': hgvs_string, 'i': i}
            )
        else:
            hgvs_json_map[hgvs_string] = row

    return header, hgvs_json_map

# --------------------------------------------------------------------------- #
#                           Accession Validators
# --------------------------------------------------------------------------- #
def validate_keyword(value):
    pass


def validate_pubmed(value):
    pass


def validate_sra(value):
    pass


def validate_doi(value):
    pass


def validate_keyword_list(values):
    for value in values:
        validate_keyword(value)


def validate_pubmed_list(values):
    for value in values:
        validate_pubmed(value)


def validate_sra_list(values):
    for value in values:
        validate_sra(value)


def validate_doi_list(values):
    for value in values:
        validate_doi(value)


def validate_target(value):
    pass


def validate_target_organism(value):
    pass
