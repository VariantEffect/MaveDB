import datetime
import idutils
import metapub
from eutils.exceptions import EutilsNCBIError

from django.db import models

import genome.models as genome_models

from core.models import TimeStampedModel

from metadata.validators import (
    validate_ensembl_identifier,
    validate_refseq_identifier,
    validate_uniprot_identifier,
)


RELATED_FIELD_NAME = "associated_{}s"


def _is_attached(instance):
    i = instance
    has_scoresets = False if i.get_associated('scoreset') is None \
        else i.get_associated('scoreset').count() > 0
    has_experiments = False if i.get_associated('experiment') is None \
        else i.get_associated('experiment').count() > 0
    has_experimentsets = False if i.get_associated('experimentset') is None \
        else i.get_associated('experimentset').count() > 0
    has_targets = False if i.get_associated('targetgene') is None \
        else i.get_associated('targetgene').count() > 0
    has_maps = False if i.get_associated('referencegenome') is None \
        else i.get_associated('referencegenome').count() > 0
    return has_maps or has_targets or has_scoresets or \
           has_experiments or has_experimentsets


class Keyword(TimeStampedModel):
    """
    This class represents a keyword that can be associated with an
    experiment or scoreset.

    Attributes
    ----------
    creation_date : `models.DateField`
        The date of instantiation.

    text : `models.TextField`
        The free-form textual representation of the keyword.
    """
    creation_date = models.DateField(blank=False, default=datetime.date.today)
    text = models.CharField(
        blank=False,
        null=False,
        default=None,
        unique=True,
        max_length=256,
        verbose_name="Keyword",
    )

    @staticmethod
    class Meta:
        ordering = ['-creation_date']
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"

    def __str__(self):
        return self.text

    @classmethod
    def tracked_fields(cls):
        return "text",

    def get_associated(self, model):
        attr = RELATED_FIELD_NAME.format(model)
        if hasattr(self, attr):
            return getattr(self, attr).all()
        else:
            return None
        
    def get_association_count(self):
        experimentsets = self.get_associated('experimentset')
        experiments = self.get_associated('experiment')
        scoresets = self.get_associated('scoreset')
        return sum([
            qs.count() for qs in [experimentsets, experiments, scoresets]
            if qs is not None
        ])
    
    def is_attached(self):
        return _is_attached(self)


class ExternalIdentifier(TimeStampedModel):
    """
    This class represents a textual representation of an identifier from an
    external database that can be associated with a target in an experiment.

    Attributes
    ----------
    identifier : `models.TextField`
        The free-form textual representation of the identifier from another
        database.

    dbname : `models.TextField`
        The name of the external database.

    dbversion : `models.CharField`
        The database version identifier.

    url : `models.URLField`
        The URL for the resource in the other database. Optional.
    """
    DATABASE_NAME = None
    IDUTILS_SCHEME = None

    identifier = models.CharField(
        blank=False,
        null=False,
        default=None,
        unique=True,
        max_length=256,
        verbose_name="Identifier",
    )
    dbname = models.CharField(
        blank=False,
        null=False,
        default=None,
        max_length=256,
        verbose_name='Database name',
    )
    dbversion = models.CharField(
        blank=True,
        null=True,
        default=None,
        max_length=256,
        verbose_name="Database version",
    )
    url = models.URLField(
        blank=True,
        null=True,
        default=None,
        max_length=256,
        verbose_name='Identifier URL',
    )

    class Meta:
        abstract = True
        ordering = ['-creation_date']
        verbose_name = "Other identifier"
        verbose_name_plural = "Other identifiers"

    @classmethod
    def tracked_fields(cls):
        return 'identifier', 'url', 'dbversion',

    def __str__(self):
        return "{}".format(self.identifier)

    def display_name(self):
        return "{}:{}".format(self.DATABASE_NAME, self.identifier)

    def format_url(self):
        if self.IDUTILS_SCHEME is not None:
            return idutils.to_url(self.identifier, self.IDUTILS_SCHEME)
        else:
            raise NotImplementedError()

    def save(self, *args, **kwargs):
        # The 'pk' is 'id' for an ExternalIdentifier, which is an
        # auto-incrementing integer field. It will be None until the
        # instance is saved for the first time.
        if self.pk is None:
            if self.IDUTILS_SCHEME is not None:
                self.identifier = idutils.normalize_pid(
                    self.identifier, self.IDUTILS_SCHEME)
            if not self.url:
                self.url = self.format_url()
            self.dbname = self.DATABASE_NAME
        super().save(*args, **kwargs)

    def get_associated(self, model_class_name):
        attr = RELATED_FIELD_NAME.format(model_class_name.lower())
        if hasattr(self, attr):
            return getattr(self, attr).all()
        else:
            return None

    def is_attached(self):
        return _is_attached(self)
    

class SraIdentifier(ExternalIdentifier):
    """
    An SRA or BioProject accession number.

    See Also
    --------
    Details of the SRA accession formats can be found
    `here <https://www.ncbi.nlm.nih.gov/books/NBK56913/#search.what_do_the_different_sra_accessi>`_

    """
    DATABASE_NAME = "SRA"

    class Meta:
        verbose_name = "SRA accession"
        verbose_name_plural = "SRA accessions"

    def format_url(self):
        if idutils.is_sra(self.identifier):
            return idutils.to_url(self.identifier, 'sra')
        elif idutils.is_bioproject(self.identifier):
            return idutils.to_url(self.identifier, 'bioproject')
        else:
            raise AttributeError("Invalid SRA or BioProject accession "
                                 "'{}'".format(self.identifier))


class DoiIdentifier(ExternalIdentifier):
    """
    A DOI identifier.
    """
    DATABASE_NAME = "DOI"
    IDUTILS_SCHEME = "doi"

    class Meta:
        verbose_name = "DOI"
        verbose_name_plural = "DOIs"


class PubmedIdentifier(ExternalIdentifier):
    """
    A PubMed identifier.
    """
    DATABASE_NAME = "PubMed"
    IDUTILS_SCHEME = "pmid"

    class Meta:
        verbose_name = "PubMed identifier"
        verbose_name_plural = "PubMed identifiers"

    reference_html = models.TextField(
        blank=True,
        null=True,
        default=None,
        verbose_name='Formatted reference'
    )

    def format_reference_html(self):
        fetch = metapub.PubMedFetcher()
        try:
            article = fetch.article_by_pmid(self.identifier)
        except EutilsNCBIError:
            reference = "Unable to retrieve PubMed ID " \
                        "'{}'".format(self.identifier)
        else:
            reference = article.citation_html
        return reference

    def save(self, *args, **kwargs):
        # The 'pk' is 'id' for an ExternalIdentifier, which is an
        # auto-incrementing integer field. It will be None until the
        # instance is saved for the first time.
        if self.pk is None:
            if not self.reference_html:
                self.reference_html = self.format_reference_html()
        super().save(*args, **kwargs)


class GenomeIdentifier(ExternalIdentifier):
    """
    An NCBI RefSeq or GenBank genome accession number.
    """
    DATABASE_NAME = "GenomeAssembly"
    IDUTILS_SCHEME = "genome"

    class Meta:
        verbose_name = "Genome assembly accession"
        verbose_name_plural = "Genome assembly accessions"


class RefseqIdentifier(ExternalIdentifier):
    """
    An NCBI RefSeq accession number.
    """
    DATABASE_NAME = "RefSeq"
    IDUTILS_SCHEME = "refseq"

    class Meta:
        verbose_name = "RefSeq accession"
        verbose_name_plural = "RefSeq accessions"


class EnsemblIdentifier(ExternalIdentifier):
    """
    An Ensembl accession number.
    """
    DATABASE_NAME = "Ensembl"
    IDUTILS_SCHEME = "ensembl"

    class Meta:
        verbose_name = "Ensembl accession"
        verbose_name_plural = "Ensembl accessions"


class UniprotIdentifier(ExternalIdentifier):
    """
    A UniProt accession number.
    """
    DATABASE_NAME = "UniProt"
    IDUTILS_SCHEME = "uniprot"

    class Meta:
        verbose_name = "UniProt accession"
        verbose_name_plural = "UniProt accessions"


# Offsets
# --------------------------------------------------------------------------- #
class AnnotationOffset(models.Model):
    """
    An offset value unique to an :class:`ExternalIdentifier` and a
    :class:`TargetGene`.
    """
    class Meta:
        abstract = True
        unique_together = ('target', 'identifier',)

    def __str__(self):
        return "{}Offset(target={}, identifier={}, offset={})".format(
            self.identifier_db, self.target, self.identifier, self.offset
        )

    offset = models.PositiveIntegerField(
        blank=True,
        null=False,
        default=0,
        verbose_name='Wild-type offset',
    )
    target = models.ForeignKey(
        to=genome_models.TargetGene,
        on_delete=models.CASCADE,
        default=None,
        null=False,
        verbose_name='Target gene',
        related_name='%(class)s',
    )

    @property
    def identifier_db(self):
        if self.target:
            return self.identifier.dbname
        return None

    @property
    def identifier_version(self):
        if self.target:
            return self.identifier.dbversion
        return None


class UniprotOffset(AnnotationOffset):
    """
    An offset value unique to an :class:`UniprotIdentifier` and a
    :class:`TargetGene`.
    """
    identifier = models.ForeignKey(
        to=UniprotIdentifier,
        on_delete=models.CASCADE,
        default=None,
        null=False,
        verbose_name='UniProt accession',
        related_name='offset',
        validators=[validate_uniprot_identifier],
    )


class RefseqOffset(AnnotationOffset):
    """
    An offset value unique to an :class:`RefseqIdentifier` and a
    :class:`TargetGene`.
    """
    identifier = models.ForeignKey(
        to=RefseqIdentifier,
        on_delete=models.CASCADE,
        default=None,
        null=False,
        verbose_name='RefSeq accession',
        related_name='offset',
        validators=[validate_refseq_identifier],
    )


class EnsemblOffset(AnnotationOffset):
    """
    An offset value unique to an :class:`EnsemblIdentifier` and a
    :class:`TargetGene`.
    """
    identifier = models.ForeignKey(
        to=EnsemblIdentifier,
        on_delete=models.CASCADE,
        default=None,
        null=False,
        verbose_name='Ensembl accession',
        related_name='offset',
        validators=[validate_ensembl_identifier],
    )