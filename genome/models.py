from django.db import models, transaction
from django.db.models import QuerySet
from django.utils.translation import ugettext_lazy as _

from core.models import TimeStampedModel
from metadata.models import (
    EnsemblIdentifier, RefseqIdentifier
)

from .validators import (
    validate_wildtype_sequence, min_start_validator,
    validate_gene_name, validate_genome_short_name, validate_species_name,
    validate_strand, validate_chromosome, min_end_validator
)


class TargetGene(TimeStampedModel):
    """
    Models a target gene, defining the wild-type sequence, a free-text name
    and a collection of annotations relating the gene to reference genomes,
    which can be from different species.

    Parameters
    ----------
    wt_sequence : :class:`models.ForeignKey`
        An instance of :class:`WildTypeSequence` defining the wildtype sequence
        of this target gene.

    name : :class:`models.CharField`
        The name of the target gene.
    """
    class Meta:
        ordering = ['name']
        verbose_name = "Target Gene"
        verbose_name_plural = "Target Genes"

    def __str__(self):
        return self.name

    name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name='Target name',
        max_length=256,
        validators=[validate_gene_name]
    )

    wt_sequence = models.ForeignKey(
        to='genome.WildTypeSequence',
        blank=True,
        null=True,
        default=None,
        verbose_name='Wildtype Sequence'
    )

    def get_name(self):
        return self.name

    def has_wt_sequence(self):
        """Returns True if a wt_sequence instance has been associated."""
        return hasattr(self, 'wt_sequence') and self.wt_sequence is not None

    def get_wt_sequence(self):
        if self.has_wt_sequence():
            return self.wt_sequence.get_sequence()

    def set_wt_sequence(self, sequence):
        if not isinstance(sequence, WildTypeSequence):
            raise TypeError("Found {}, expected {}.".format(
                type(sequence).__name__, WildTypeSequence.__name__
            ))
        self.wt_sequence = sequence

    def annotation_count(self):
        return self.annotations.count()

    def has_annotations(self):
        return self.annotation_count() > 0

    def get_annotations(self):
        return self.annotations.all()

    def get_reference_genomes(self):
        genome_pks = set(a.genome.pk for a in self.get_annotations())
        return ReferenceGenome.objects.filter(pk__in=genome_pks)

    def get_primary_reference(self):
        return self.get_reference_genomes(
        ).filter(
            is_primary=True
        ).order_by(
            'short_name'
        ).first()

    def reference_mapping(self):
        return {
            annotation.get_genome_name(): annotation.serialise()
            for annotation in self.get_annotations()
        }


class Annotation(TimeStampedModel):
    """
    Annotations define a collection of intervals within reference genome, which
    are to be used to define how a :class:`TargetGene` maps to a particular
    reference genome.

    Parameters
    ----------
    genome : :class:`models.ForeignKey`
        The genome instance this annotation refers to.

    target : `ForeignField`
        An instance of :class:`TargetGene` this instance is associated with.
    """
    class Meta:
        verbose_name = "Annotation"
        verbose_name_plural = "Annotations"

    def __str__(self):
        return 'Annotation(genome={}, primary={})'.format(
            self.get_genome_name(), self.is_primary_annotation())

    genome = models.ForeignKey(
        to='genome.ReferenceGenome',
        blank=True,
        null=True,
        default=None,
        verbose_name='Reference genome',
        related_name='annotations'
    )

    target = models.ForeignKey(
        to=TargetGene,
        blank=True,
        null=True,
        default=None,
        verbose_name='Target',
        related_name='annotations',
        on_delete=models.CASCADE,
    )

    is_primary = models.BooleanField(
        blank=True,
        null=False,
        default=False,
        verbose_name='Primary'
    )

    def get_target(self):
        """
        Returns the target associated with this annotation otherwise None.

        Returns
        -------
        :class:`TargetGene`
        """
        return self.target

    def has_genome(self):
        """Returns True if a genome instance has been associated."""
        return hasattr(self, 'genome') and self.genome is not None

    def get_genome(self):
        """
        Return the associated genome for this annotation.

        Returns
        -------
        :class:`ReferenceGenome`
        """
        if self.has_genome():
            return self.genome

    def set_genome(self, genome):
        """
        Set the reference genome to `value`
        """
        if not isinstance(genome, ReferenceGenome):
            raise TypeError("Found {}, expected {}.".format(
                type(genome).__name__, ReferenceGenome.__name__
            ))
        self.genome = genome

    def get_genome_name(self):
        """
        Return the string name of genome associated with this annotation.
        """
        if self.get_genome():
            return self.get_genome().get_short_name()

    def get_genome_species(self):
        """
        Return the string species name of genome associated with this
        annotation.
        """
        if self.get_genome():
            return self.get_genome().get_species_name()

    def format_genome_species(self):
        """
        Return a HTML string formatting the associated genomes species name
        using italics and capitalisation.
        """
        if self.get_genome():
            return self.get_genome().format_species_name_html()

    def get_intervals(self):
        """
        Return the :class:`Interval` instances defining a mapping of
        genomic coordinates with respect to the :class:`ReferenceGenome`.

        Returns
        -------
        :class:`QuerySet`
        """
        return self.intervals.all()

    def has_intervals(self):
        """
        Returns True if this instance has associated intervals.
        """
        return self.get_intervals().count() > 0

    def set_is_primary(self, primary=True):
        """
        Sets the primary status as `primary`.
        """
        self.is_primary = primary

    def is_primary_annotation(self):
        """
        Returns True if the associated :class:`ReferenceGenome` is marked
        as primary
        """
        return self.is_primary

    def serialise(self):
        return {
            'target': self.get_target().get_name(),
            'primary': self.is_primary_annotation(),
            'reference': self.get_genome().serialise(),
            'intervals': [i.serialise() for i in self.get_intervals()]
        }


class ReferenceGenome(TimeStampedModel):
    """
    The `ReferenceGenome` specifies fields describing a specific genome (name,
    species, identifier) along with book-keeping fields such as a URL to
    a `Ensembl` entry and a version/release descriptor.

    Parameters
    ----------
    short_name : `CharField`
        The short name description of the genome. Example: 'hg38'.

    species_name : `CharField`
        The species of the genome. Example: 'Homo spaiens'

    ensembl_id : `ForeignKey`
        An :class:`EnsemblIdentifier` instance to relating to this genome.

    refseq_id : `ForeignKey`
        A :class:`RefseqIdentifier` instance to relating to this genome.
    """
    class Meta:
        ordering = ['short_name']
        verbose_name = 'Reference Genome'
        verbose_name_plural = 'Reference Genomes'

    def __str__(self):
        return self.get_short_name()

    short_name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name='Name',
        max_length=256,
        validators=[validate_genome_short_name]
    )
    species_name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name='Species',
        max_length=256,
        validators=[validate_species_name]
    )

    # Potential ExternalIdentifiers that may be linked.
    ensembl_id = models.ForeignKey(
        to=EnsemblIdentifier,
        blank=True,
        null=True,
        default=None,
        verbose_name='Ensembl identifier',
    )
    refseq_id = models.ForeignKey(
        to=RefseqIdentifier,
        blank=True,
        null=True,
        default=None,
        verbose_name='RefSeq identifier',
    )

    def get_identifier_url(self):
        id_ = self.get_identifier_instance()
        if id_ is not None:
            return id_.url
        return None

    def get_identifier(self):
        id_ = self.get_identifier_instance()
        if id_ is not None:
            return id_.identifier
        return None

    def get_identifier_database(self):
        id_ = self.get_identifier_instance()
        if id_ is not None:
            return id_.dbname
        return None

    def get_identifier_instance(self):
        if self.ensembl_id is not None:
            return self.get_ensembl_id()
        elif self.refseq_id is not None:
            return self.get_refseq_id()
        return None

    def get_refseq_id(self):
        return self.refseq_id

    def get_ensembl_id(self):
        return self.ensembl_id

    def get_short_name(self):
        return self.short_name

    def get_species_name(self):
        return self.species_name

    def format_species_name_html(self):
        return "<i>{}</i>".format(self.get_species_name().capitalize())

    def serialise(self):
        return {
            'name': self.get_short_name(),
            'species': self.get_species_name(),
            'external_identifier': {
                'dbname': self.get_identifier_database(),
                'identifier': self.get_identifier(),
                'url': self.get_identifier_url()
            },
        }


class Interval(TimeStampedModel):
    """
    Represents a specific region within the reference genome, including
    chromosome and strand. All intervals use 1-based indexing.

    Parameters
    ----------
    start : `PositiveIntegerField`
        The starting base position within a reference genome (inclusive).

    end : `PositiveIntegerField`
        The ending base position within a reference genome (inclusive).

    chromosome : `PositiveIntegerField`
        The chromosome number this interval is one.

    strand : `CharField, choices: {'F', 'R'}
        The strand this interval is defined with respect to.

    annotation : `ForeignKey`
        An annotation instance that this interval is associated with.
    """
    STRAND_CHOICES = (
        ('F', 'Forward'),  # (database value, verbose value)
        ('R', 'Reverse')
    )

    class Meta:
        ordering = ['start']
        verbose_name = "Reference Interval"
        verbose_name_plural = "Reference Intervals"

    def __str__(self):
        return (
            'Interval(start={start}, end={end}, ' 
            'chromosome={chr}, strand={strand})'.format(
                start=self.get_start(), end=self.get_end(),
                chr=self.get_chromosome(), strand=self.get_strand()
            )
        )

    # Don't use __eq__ for Django models. This might break Django
    # internals for forms/views etc.
    def equals(self, other):
        this = (
            self.start, self.end,
            self.chromosome.lower(), self.get_strand()
        )
        other = (
            other.start, other.end,
            other.chromosome.lower(), other.get_strand()
        )
        return this == other

    start = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Start',
        validators=[min_start_validator]
    )
    end = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='End (inclusive)',
        validators=[min_end_validator]
    )
    chromosome = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Chromosome identifier',
        max_length=32,
        validators=[validate_chromosome]
    )
    strand = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Strand',
        choices=STRAND_CHOICES,
        max_length=1,
        validators=[validate_strand]
    )
    annotation = models.ForeignKey(
        to=Annotation,
        default=None,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='intervals'
    )

    def get_start(self, offset=0):
        return self.start + offset

    def get_end(self, offset=0):
        return self.end + offset

    def get_chromosome(self):
        return self.chromosome

    def get_strand(self):
        return self.strand.upper()

    def get_annotation(self):
        if hasattr(self, 'annotation'):
            return self.annotation
        return None

    def set_annotation(self, annotation):
        self.annotation = annotation

    def serialise(self):
        return {
            'start': self.get_start(),
            'end': self.get_end(),
            'chromosome': self.get_chromosome(),
            'strand': self.get_strand()
        }


class WildTypeSequence(TimeStampedModel):
    """
    Basic model specifying a wild-type sequence.

    Parameters
    ----------
    sequence : `models.CharField`
        The wild type DNA sequence that is related to the `target`. Will
        be converted to upper-case upon instantiation.
    """
    class Meta:
        verbose_name = "Wild Type Sequence"
        verbose_name_plural = "Wild Type Sequences"

    def __str__(self):
        return self.get_sequence()

    sequence = models.TextField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Wildtype sequence",
        validators=[validate_wildtype_sequence],
    )

    def get_sequence(self):
        return self.sequence.upper()

    def save(self, *args, **kwargs):
        if self.sequence is not None:
            self.sequence = self.sequence.upper()
        super().save(*args, **kwargs)

    def serialise(self):
        return {'sequence': self.get_sequence()}
