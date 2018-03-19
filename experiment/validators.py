
import re
from django.core.exceptions import ValidationError

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


def valid_wildtype_sequence(seq):
    if not re.fullmatch(DNA_SEQ_RE, seq):
        raise ValidationError(
            "'%(seq)s' is not a valid wild type sequence.",
            params={"seq": seq}
        )
