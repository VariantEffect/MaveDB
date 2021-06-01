import re

from django.core.exceptions import ValidationError

MAVEDB_EXPERIMENTSET_URN_DIGITS = 8
MAVEDB_TMP_URN_DIGITS = 16
MAVEDB_URN_MAX_LENGTH = 64
MAVEDB_URN_NAMESPACE = "mavedb"


# Temp URN patterns
# --------------------------------------------------------------------------- #
MAVEDB_TMP_URN_PATTERN = r"^tmp:[A-Za-z0-9]{{{width}}}$".format(
    width=MAVEDB_TMP_URN_DIGITS
)
MAVEDB_TMP_URN_RE = re.compile(MAVEDB_TMP_URN_PATTERN)


# Experimentset Pattern/Compiled RE
MAVEDB_EXPERIMENTSET_URN_PATTERN = r"^urn:{namespace}:\d{{{width}}}$".format(
    namespace=MAVEDB_URN_NAMESPACE, width=MAVEDB_EXPERIMENTSET_URN_DIGITS
)
MAVEDB_EXPERIMENTSET_URN_RE = re.compile(MAVEDB_EXPERIMENTSET_URN_PATTERN)

# Experiment Pattern/Compiled RE
MAVEDB_EXPERIMENT_URN_PATTERN = r"{pattern}-([a-z]+|0)$".format(
    pattern=MAVEDB_EXPERIMENTSET_URN_PATTERN[:-1]
)
MAVEDB_EXPERIMENT_URN_RE = re.compile(MAVEDB_EXPERIMENT_URN_PATTERN)

# Scoreset Pattern/Compiled RE
MAVEDB_SCORESET_URN_PATTERN = r"{pattern}-\d+$".format(
    pattern=MAVEDB_EXPERIMENT_URN_PATTERN[:-1]
)
MAVEDB_SCORESET_URN_RE = re.compile(MAVEDB_SCORESET_URN_PATTERN)

# Variant Pattern/Compiled RE
MAVEDB_VARIANT_URN_PATTERN = r"{pattern}#\d+$".format(
    pattern=MAVEDB_SCORESET_URN_PATTERN[:-1]
)
MAVEDB_VARIANT_URN_RE = re.compile(MAVEDB_VARIANT_URN_PATTERN)

# Any Pattern/Compiled RE
MAVEDB_ANY_URN_PATTERN = "|".join(
    [
        r"({pattern})".format(pattern=p)
        for p in (
            MAVEDB_EXPERIMENTSET_URN_PATTERN,
            MAVEDB_EXPERIMENT_URN_PATTERN,
            MAVEDB_SCORESET_URN_PATTERN,
            MAVEDB_VARIANT_URN_PATTERN,
            MAVEDB_TMP_URN_PATTERN,
        )
    ]
)
MAVEDB_ANY_URN_RE = re.compile(MAVEDB_ANY_URN_PATTERN)


def validate_mavedb_urn(urn):
    if not MAVEDB_ANY_URN_RE.match(urn):
        raise ValidationError(
            "%(urn)s is not a valid urn.", params={"urn": urn}
        )


def validate_mavedb_urn_experimentset(urn):
    if not (
        MAVEDB_EXPERIMENTSET_URN_RE.match(urn) or MAVEDB_TMP_URN_RE.match(urn)
    ):
        raise ValidationError(
            "%(urn)s is not a valid Experiment Set urn.", params={"urn": urn}
        )


def validate_mavedb_urn_experiment(urn):
    if not (
        MAVEDB_EXPERIMENT_URN_RE.match(urn) or MAVEDB_TMP_URN_RE.match(urn)
    ):
        raise ValidationError(
            "%(urn)s is not a valid Experiment urn.", params={"urn": urn}
        )


def validate_mavedb_urn_scoreset(urn):
    if not (MAVEDB_SCORESET_URN_RE.match(urn) or MAVEDB_TMP_URN_RE.match(urn)):
        raise ValidationError(
            "%(urn)s is not a valid score set urn.", params={"urn": urn}
        )


def validate_mavedb_urn_variant(urn):
    if not (MAVEDB_VARIANT_URN_RE.match(urn) or MAVEDB_TMP_URN_RE.match(urn)):
        raise ValidationError(
            "%(urn)s is not a valid Variant urn.", params={"urn": urn}
        )
