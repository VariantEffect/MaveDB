import re

from django.core.exceptions import ValidationError


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