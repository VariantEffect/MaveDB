import re
import idutils

from django.core.exceptions import ValidationError

from core.utilities import is_null


def validate_sra_identifier(identifier):
    if not (idutils.is_sra(identifier) or idutils.is_bioproject(identifier)):
        raise ValidationError(
            "%(id)s is not a valid SRA or BioProject accession.",
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
            "%(id)s is not a valid DOI.",
            params={"id": identifier}
        )

def validate_ensembl_identifier(identifier):
    if not idutils.is_ensembl(identifier):
        raise ValidationError(
            "%(id)s is not a valid Ensembl accession.",
            params={"id": identifier}
        )


def validate_uniprot_identifier(identifier):
    if not idutils.is_uniprot(identifier):
        raise ValidationError(
            "%(id)s is not a valid UniProt accession.",
            params={"id": identifier}
        )


def validate_refseq_identifier(identifier):
    if not idutils.is_refseq(identifier):
        raise ValidationError(
            "%(id)s is not a valid RefSeq accession.",
            params={"id": identifier}
        )


def validate_genome_identifier(identifier):
    if not idutils.is_genome(identifier):
        raise ValidationError(
            "%(id)s is not a valid GenBank or RefSeq genome assembly.",
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
