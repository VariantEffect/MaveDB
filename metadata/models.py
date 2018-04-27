import datetime
import idutils

from django.db import models

import genome.models as genome_models

from core.models import TimeStampedModel

from metadata.validators import (
    SRA_BIOPROJECT_RE, SRA_STUDY_RE,
    SRA_EXPERIMENT_RE, SRA_RUN_RE,
    validate_ensembl_identifier,
    validate_refseq_identifier,
    validate_uniprot_identifier,
)


class Keyword(TimeStampedModel):
    """
    This class represents a keyword that can be associated with an
    experiment or scoreset.

    Parameters
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

    def get_associated(self, model):
        attr = 'associated_{}s'.format(model)
        return getattr(self, attr).all()


class ExternalIdentifier(TimeStampedModel):
    """
    This class represents a textual representation of an identifier from an
    external database that can be associated with a target in an experiment.

    Parameters
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

    def __str__(self):
        return "{}:{}".format(self.DATABASE_NAME, self.identifier)

    def display_name(self):
        return "{}".format(self.identifier)

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
            self.url = self.format_url()
            self.dbname = self.DATABASE_NAME
        super().save(*args, **kwargs)

    def get_associated(self, model):
        attr = 'associated_{}s'.format(model)
        return getattr(self, attr).all()


class SraIdentifier(ExternalIdentifier):
    """
    An SRA identifier.

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
        if SRA_BIOPROJECT_RE.match(self.identifier):
            return "https://www.ncbi.nlm.nih.gov/" \
                   "bioproject/{id}".format(id=self.identifier)
        elif SRA_STUDY_RE.match(self.identifier):
            return "http://trace.ncbi.nlm.nih.gov/" \
                   "Traces/sra/sra.cgi?study={id}" \
                   "".format(id=self.identifier)
        elif SRA_EXPERIMENT_RE.match(self.identifier):
            return "https://www.ncbi.nlm.nih.gov/" \
                   "sra/{id}?report=full".format(id=self.identifier)
        elif SRA_RUN_RE.match(self.identifier):
            return "http://trace.ncbi.nlm.nih.gov/" \
                   "Traces/sra/sra.cgi?" \
                   "cmd=viewer&m=data&s=viewer&run={id}" \
                   "".format(id=self.identifier)
        else:
            raise ValueError("Invalid SRA identifier '{}'".format(
                self.identifier))


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
        # TODO: Write this.
        return ""

    def save(self, *args, **kwargs):
        # The 'pk' is 'id' for an ExternalIdentifier, which is an
        # auto-incrementing integer field. It will be None until the
        # instance is saved for the first time.
        if self.pk is None:
            self.reference_html = self.format_reference_html()
        super().save(*args, **kwargs)


class GenomeIdentifier(ExternalIdentifier):
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

    class Meta:
        verbose_name = "RefSeq accession"
        verbose_name_plural = "RefSeq accessions"

    def format_url(self):
        pass


class EnsemblIdentifier(ExternalIdentifier):
    """
    An Ensembl accession number.
    """
    DATABASE_NAME = "Ensembl"

    class Meta:
        verbose_name = "Ensembl accession"
        verbose_name_plural = "Ensembl accessions"

    def format_url(self):
        pass
    

class UniprotIdentifier(ExternalIdentifier):
    """
    A UniProt accession number.
    """
    DATABASE_NAME = "UniProt"

    class Meta:
        verbose_name = "UniProt accession"
        verbose_name_plural = "UniProt accessions"

    def format_url(self):
        pass


# Offsets
# --------------------------------------------------------------------------- #
class AnnotationOffset(models.Model):
    """
    An offset value unique to an :class:`ExternalIdentifier` and a
    :class:`TargetGene`.
    """
    class Meta:
        abstract = True

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
    target = models.OneToOneField(
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
    identifier = models.OneToOneField(
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
    identifier = models.OneToOneField(
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
    identifier = models.OneToOneField(
        to=EnsemblIdentifier,
        on_delete=models.CASCADE,
        default=None,
        null=False,
        verbose_name='Ensembl accession',
        related_name='offset',
        validators=[validate_ensembl_identifier],
    )