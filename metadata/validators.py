import re

from django.core.exceptions import ValidationError


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

def validate_sra_identifier(identifier):
    if not SRA_ANY_RE.match(identifier):
        raise ValidationError(
            "%(id)s is not a valid SRA identifier.",
            params={"id": identifier}
        )


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
