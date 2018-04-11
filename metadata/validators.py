import re
import idutils

from django.core.exceptions import ValidationError

from core.utilities import is_null

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


def validate_keyword(kw):
    if not isinstance(kw, str):
        raise ValidationError(
            "%(kw)s is not a valid keyword. Keywords must be strings.",
            params={"kw": kw}
        )


def validate_pubmed_identifier(identifier):
    if not idutils.is_pmid(identifier):
        raise ValidationError(
            "%(id)s is not a valid PubMed identifier.",
            params={"id": identifier}
        )


def validate_doi_identifier(identifier):
    if not idutils.is_doi(identifier):
        raise ValidationError(
            "%(id)s is not a valid DOI identifier.",
            params={"id": identifier}
        )

def validate_ensembl_identifier(identifier):
    if not identifier:
        raise ValidationError(
            "%(id)s is not a valid Ensembl identifier.",
            params={"id": identifier}
        )


def validate_uniprot_identifier(identifier):
    if not identifier:
        raise ValidationError(
            "%(id)s is not a valid UniProt identifier.",
            params={"id": identifier}
        )


def validate_refseq_identifier(identifier):
    if not identifier:
        raise ValidationError(
            "%(id)s is not a valid RefSeq identifier.",
            params={"id": identifier}
        )


def validate_keyword_list(values):
    for value in values:
        if not is_null(value):
            validate_keyword(value)


def validate_pubmed_list(values):
    for value in values:
        if not is_null(value):
            validate_pubmed_identifier(value)


def validate_sra_list(values):
    for value in values:
        if not is_null(value):
            validate_sra_identifier(value)


def validate_doi_list(values):
    for value in values:
        if not is_null(value):
            validate_doi_identifier(value)


def validate_ensembl_list(values):
    for value in values:
        if not is_null(value):
            validate_ensembl_list(value)


def validate_refseq_list(values):
    for value in values:
        if not is_null(value):
            validate_refseq_list(value)


def validate_uniprot_list(values):
    for value in values:
        if not is_null(value):
            validate_uniprot_identifier(value)