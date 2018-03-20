
import re
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

DNA_SEQ_RE = r'[ATGCatgc]+'

MAVEDB_EXPERIMENTSET_URN_DIGITS = 8
MAVEDB_URN_MAX_LENGTH = 64
MAVEDB_URN_NAMESPACE = "mavedb"

MAVEDB_EXPERIMENTSET_URN_PATTERN = r'^urn:{namespace}:\d{{{width}}}$'.format(
    namespace=MAVEDB_URN_NAMESPACE,
    width=MAVEDB_EXPERIMENTSET_URN_DIGITS
)

MAVEDB_EXPERIMENT_URN_PATTERN = r'{pattern}-[a-z]+$'.format(
    pattern=MAVEDB_EXPERIMENTSET_URN_PATTERN[:-1]
)

MAVEDB_SCORESET_URN_PATTERN = r'{pattern}-\d+$'.format(
    pattern=MAVEDB_EXPERIMENT_URN_PATTERN[:-1]
)

MAVEDB_VARIANT_URN_PATTERN = r'{pattern}#\d+$'.format(
    pattern=MAVEDB_SCORESET_URN_PATTERN[:-1]
)

MAVEDB_ANY_URN_PATTERN = '|'.join([r'({pattern})'.format(pattern=p) for p in (
    MAVEDB_EXPERIMENTSET_URN_PATTERN,
    MAVEDB_EXPERIMENT_URN_PATTERN,
    MAVEDB_SCORESET_URN_PATTERN,
    MAVEDB_VARIANT_URN_PATTERN)
])

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


class Constants(object):
    NAN_COL_VALUES = set(['nan', 'na', 'none', '', ' '])
    HGVS_COLUMN = "hgvs"
    COUNT_COLUMN = "count"
    SCORES_DATA = "scores_data"
    COUNTS_DATA = "counts_data"
    SCORES_KEY = 'score'
    COUNTS_KEY = 'count'


def is_null(value):
    return str(value).strip().lower() in Constants.NAN_COL_VALUES


# --------------------------------------------------------------------------- #
#                           URN Validators
# --------------------------------------------------------------------------- #
def valid_mavedb_urn(accession):
    if not re.match(MAVEDB_ANY_URN_PATTERN, accession):
        raise ValidationError(
            "%(accession)s is not a valid accession.",
            params={"accession": accession}
        )


def valid_mavedb_urn_experimentset(accession):
    if not re.match(MAVEDB_EXPERIMENTSET_URN_PATTERN, accession):
        raise ValidationError(
            "%(accession)s is not a valid Experiment Set accession.",
            params={"accession": accession}
        )


def valid_mavedb_urn_experiment(accession):
    if not re.match(MAVEDB_EXPERIMENT_URN_PATTERN, accession):
        raise ValidationError(
            "%(accession)s is not a valid Experiment accession.",
            params={"accession": accession}
        )


def valid_mavedb_urn_scoreset(accession):
    if not re.match(MAVEDB_SCORESET_URN_PATTERN, accession):
        raise ValidationError(
            "%(accession)s is not a valid Score Set accession.",
            params={"accession": accession}
        )


def valid_mavedb_urn_variant(accession):
    if not re.match(MAVEDB_VARIANT_URN_PATTERN, accession):
        raise ValidationError(
            "%(accession)s is not a valid Variant accession.",
            params={"accession": accession}
        )


# --------------------------------------------------------------------------- #
#                           Sequence/HGVS Validators
# --------------------------------------------------------------------------- #
def valid_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_RE, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )


def valid_hgvs_string(string):
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
   #         _("Variant '%(variant)s' is not a valid HGVS string."),
   #         params={'variant': string}
   #     )
    return

# --------------------------------------------------------------------------- #
#                           ScoreSet Validators
# --------------------------------------------------------------------------- #
csv_validator = FileExtensionValidator(allowed_extensions=['csv'])

def valid_scoreset_score_data_input(file):
    header_line = file.readline()
    if isinstance(header_line, bytes):
        header_line = header_line.decode()

    expected_header = [Constants.HGVS_COLUMN]
    header = [l.strip() for l in header_line.strip().split(',')]
    try:
        valid_header = header[0] == expected_header[0]
        if not valid_header:
            raise ValueError()
    except:
        raise ValidationError(
            _(
                "Score data header requires the column 'hgvs'. Ensure the "
                "columns are separated by a comma, and that 'hgvs' is the "
                "first column."
            )
        )
    if file.size < 4:
        raise ValidationError(_("Dataset cannot be empty."))


def valid_scoreset_count_data_input(file):
    header_line = file.readline()
    if isinstance(header_line, bytes):
        header_line = header_line.decode()

    expected_header = [Constants.HGVS_COLUMN]
    header = [l.strip() for l in header_line.strip().split(',')]
    try:
        valid_header = (header[0] == expected_header[0])
        if not valid_header:
            raise ValueError()
    except:
        raise ValidationError(
            _(
                "Count data header requires the column 'hgvs'. Ensure the "
                "columns are separated by a comma, and that 'hgvs' is the "
                "first column."
            )
        )
    if file.size < 4:
        raise ValidationError(_("Dataset cannot be empty."))


def valid_scoreset_json(json_object, has_counts_data=False):
    if Constants.SCORES_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": Constants.SCORES_KEY}
        )
    if Constants.COUNTS_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": Constants.COUNTS_KEY}
        )
    expected = [Constants.SCORES_KEY, Constants.COUNTS_KEY]
    extras = [k for k in json_object.keys() if k not in set(expected)]
    if len(extras) > 0:
        extras = [k for k in json_object.keys() if k not in expected]
        raise ValidationError(
            _("%(data)s has additional unexpected keys '%(extras)s'."),
            params={"data": json_object, "extras": extras}
        )

    # Check the correct data types are given.
    if not isinstance(json_object[Constants.SCORES_KEY], list):
        type_ = type(json_object[Constants.SCORES_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a list not %(type)s."),
            params={"data": json_object, "type": type_}
        )
    if not isinstance(json_object[Constants.COUNTS_KEY], list):
        type_ = type(json_object[Constants.COUNTS_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a list not %(type)s."),
            params={"data": json_object, "type": type_}
        )

    # Check the correct inner data types are given.
    try:
        if not isinstance(json_object[Constants.SCORES_KEY][0], str):
            raise ValidationError("")
    except IndexError:
        raise ValidationError(
            _("No header could be found for '%(key)s' dataset."),
            params={"key": Constants.SCORES_KEY}
        )
    except ValidationError:
        type_ = type(json_object[Constants.SCORES_KEY][0]).__name__
        raise ValidationError(
            _("Header values must be strings not '%(type)s'."),
            params={"type": type_}
        )

    try:
        if not isinstance(json_object[Constants.COUNTS_KEY][0], str):
            raise ValidationError()
    except IndexError:
        if has_counts_data:
            raise ValidationError(
                _("No header could be found for '%(key)s' dataset."),
                params={"key": Constants.COUNTS_KEY}
            )
    except ValidationError:
        type_ = type(json_object[Constants.COUNTS_KEY][0]).__name__
        raise ValidationError(
            _("Header values must be strings not '%(type)s'."),
            params={"type": type_}
        )


def valid_variant_json(json_object):
    if Constants.SCORES_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": Constants.SCORES_KEY}
        )
    if Constants.COUNTS_KEY not in json_object.keys():
        raise ValidationError(
            _("%(data)s is missing the required key '%(key)s'."),
            params={"data": json_object, "key": Constants.COUNTS_KEY}
        )
    expected = [Constants.SCORES_KEY, Constants.COUNTS_KEY]
    extras = [k for k in json_object.keys() if k not in set(expected)]
    if len(extras) > 0:
        extras = [k for k in json_object.keys() if k not in expected]
        raise ValidationError(
            _("%(data)s has additional unexpected keys '%(extras)s'."),
            params={"data": json_object, "extras": extras}
        )

    # Check the correct data types are given.
    if not isinstance(json_object[Constants.SCORES_KEY], dict):
        type_ = type(json_object[Constants.SCORES_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a dict not %(type)s."),
            params={"data": json_object, "type": type_}
        )
    if not isinstance(json_object[Constants.COUNTS_KEY], dict):
        type_ = type(json_object[Constants.COUNTS_KEY]).__name__
        raise ValidationError(
            _("%(data)s dictionary values must be a dict not %(type)s."),
            params={"data": json_object, "type": type_}
        )


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