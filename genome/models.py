from django.db import models
from django.db.models import QuerySet

from core.models import TimeStampedModel

from .validators import (
    validate_wildtype_sequence, min_start_validator,
    validate_gene_name, validate_genome_short_name, validate_species_name,
    validate_strand, validate_chromosome, min_end_validator
)


class TargetGene(TimeStampedModel):
    """
    Models a target gene, defining the wild-type sequence, a free-text name
    and a collection of reference_maps relating the gene to reference genomes,
    which can be from different species.

    The fields `wt_sequence` and `scoreset` are allowed
    to be saved as `None` to allow complex form handling but this *should*
    be transient within the view-validate-commit form upload loop.

    Parameters
    ----------
    wt_sequence : `models.OneToOneField`
        An instance of :class:`WildTypeSequence` defining the wildtype sequence
        of this target gene.

    scoreset : `models.OneToOneField`
        One to one relationship associating this target with a scoreset. If
        this scoreset is deleted, the target and associated reference_maps/intervals
        will also be deleted.

    name : `models.CharField`
        The name of the target gene.
    """
    class Meta:
        ordering = ['name']
        verbose_name = "Target Gene"
        verbose_name_plural = "Target Genes"

    def __str__(self):
        return self.get_name()

    name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name='Target name',
        max_length=256,
        validators=[validate_gene_name],
    )

    scoreset = models.OneToOneField(
        to='dataset.ScoreSet',
        on_delete=models.CASCADE,
        null=False,
        default=None,
        blank=False,
        related_name='target',
    )

    wt_sequence = models.OneToOneField(
        to='genome.WildTypeSequence',
        blank=False,
        null=False,
        default=None,
        verbose_name='Wild-type Sequence',
        related_name='target',
    )

    # External Identifiers
    # ----------------------------------------------------------------------- #
    uniprot_id = models.OneToOneField(
        to='metadata.UniprotIdentifier',
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name='associated_%(class)ss',
    )
    ensembl_id = models.OneToOneField(
        to='metadata.EnsemblIdentifier',
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name='associated_%(class)ss',
    )
    refseq_id = models.OneToOneField(
        to='metadata.RefseqIdentifier',
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name='associated_%(class)ss',
    )

    def get_name(self):
        return self.name

    def get_unique_name(self):
        """Target name appended to its scoreset urn."""
        return '{} | {}'.format(self.name, self.get_scoreset_urn())

    def get_scoreset_urn(self):
        if self.scoreset:
            return self.scoreset.urn

    def get_wt_sequence_string(self):
        if self.wt_sequence:
            return self.wt_sequence.get_sequence()

    def get_wt_sequence(self):
        if hasattr(self, 'wt_sequence'):
            return self.wt_sequence

    def set_wt_sequence(self, sequence):
        if not isinstance(sequence, WildTypeSequence):
            raise TypeError("Found {}, expected {} or str.".format(
                type(sequence).__name__, WildTypeSequence.__name__
            ))
        self.wt_sequence = sequence

    def reference_map_count(self):
        return self.reference_maps.count()

    def get_reference_maps(self):
        return self.reference_maps.all()

    def get_reference_genomes(self):
        genome_pks = set(a.genome.pk for a in self.get_reference_maps())
        return ReferenceGenome.objects.filter(pk__in=genome_pks)


class ReferenceMap(TimeStampedModel):
    """
    Annotations define a collection of intervals within reference genome, which
    are to be used to define how a :class:`TargetGene` maps to a particular
    reference genome.

    The fields `genome` and `target` are allowed to be saved as `None` to allow
    complex form handling but this *should* be transient within the
    view-validate-commit form upload loop.

    Parameters
    ----------
    genome : `models.ForeignKey`
        The genome instance this reference_map refers to.

    target : `models.ForeignField`
        An instance of :class:`TargetGene` this instance is associated with.

    is_primary : `models.BooleanField`
        If True, indicates that this reference_map refers to the genome from which
        the associated `target` comes from.
    """
    class Meta:
        verbose_name = "Reference map"
        verbose_name_plural = "Reference maps"

    def __str__(self):
        return 'ReferenceMap(genome={}, primary={})'.format(
            self.get_reference_genome_name(), self.is_primary_reference_map())

    genome = models.ForeignKey(
        to='genome.ReferenceGenome',
        blank=False,
        null=False,
        default=None,
        on_delete=models.PROTECT,
        verbose_name='Reference genome',
        related_name='associated_reference_maps',
    )

    target = models.ForeignKey(
        to='genome.TargetGene',
        blank=False,
        null=False,
        default=None,
        verbose_name='Target',
        related_name='reference_maps',
        on_delete=models.CASCADE,
    )

    is_primary = models.BooleanField(
        blank=True,
        null=False,
        default=False,
        verbose_name='Primary',
    )

    def get_target_gene(self):
        return self.target

    def set_target_gene(self, target):
        if not isinstance(target, TargetGene):
            raise TypeError("Found {}, expected {}.".format(
                type(target).__name__, TargetGene.__name__
            ))
        self.target = target

    def get_reference_genome(self):
        return self.genome

    def set_reference_genome(self, genome):
        if not isinstance(genome, ReferenceGenome):
            raise TypeError("Found {}, expected {}.".format(
                type(genome).__name__, ReferenceGenome.__name__
            ))
        self.genome = genome

    def get_reference_genome_name(self):
        if self.get_reference_genome():
            return self.get_reference_genome().get_short_name()

    def get_reference_genome_species(self):
        if self.get_reference_genome():
            return self.get_reference_genome().get_species_name()

    def format_reference_genome_species_html(self):
        """
        Return a HTML string formatting the associated genomes species name
        using italics and capitalisation.
        """
        if self.get_reference_genome():
            return self.get_reference_genome().format_species_name_html()

    def get_intervals(self):
        return self.intervals.all()

    def set_is_primary(self, primary=True):
        self.is_primary = primary

    def is_primary_reference_map(self):
        return self.is_primary


class ReferenceGenome(TimeStampedModel):
    """
    The :class:`ReferenceGenome` specifies fields describing a specific genome
    in terms of a short name, species and various external identifiers.

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
        validators=[validate_genome_short_name],
    )
    species_name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name='Species',
        max_length=256,
        validators=[validate_species_name],
    )

    # Potential ExternalIdentifiers that may be linked.
    genome_id = models.ForeignKey(
        to='metadata.GenomeIdentifier',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name='Genome assembly identifier',
        related_name='associated_%(class)ss',
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
        if self.genome_id is not None:
            return self.genome_id
        return None

    def display_name(self):
        return '{} | {}'.format(self.get_short_name(), self.get_species_name())

    def get_short_name(self):
        return self.short_name

    def get_species_name(self):
        return self.species_name

    def format_species_name_html(self):
        """
        Return a HTML string formatting the associated genomes species name
        using italics and capitalisation.
        """
        return "<i>{}</i>".format(self.get_species_name().capitalize())


class GenomicInterval(TimeStampedModel):
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

    reference_map : `ForeignKey`
        An reference_map instance that this interval is associated with.
    """
    STRAND_CHOICES = (
        ('+', '+'),  # (database value, verbose value used in UI)
        ('-', '-')
    )

    class Meta:
        ordering = ['start']
        verbose_name = "Reference interval"
        verbose_name_plural = "Reference intervals"

    def __str__(self):
        return (
            'GenomicInterval(start={start}, end={end}, ' 
            'chromosome={chr}, strand={strand})'.format(
                start=self.get_start(), end=self.get_end(),
                chr=self.get_chromosome(), strand=self.get_strand()
            )
        )

    start = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Start',
        validators=[min_start_validator],
    )
    end = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='End (inclusive)',
        validators=[min_end_validator],
    )
    chromosome = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Chromosome identifier',
        max_length=32,
        validators=[validate_chromosome],
    )
    strand = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Strand',
        choices=STRAND_CHOICES,
        max_length=1,
        validators=[validate_strand],
    )
    reference_map = models.ForeignKey(
        to='genome.ReferenceMap',
        default=None,
        blank=False,
        null=None,
        on_delete=models.CASCADE,
        related_name='intervals',
    )

    # Don't overload the __eq__ for Django models. This might break Django
    # internals for forms/views etc.
    def equals(self, other):
        """
        Compares two intervals based on `start`, `end`, lowercase `chromosome`
        and `strand`.
        """
        this = (
            self.start, self.end,
            self.chromosome.lower(), self.get_strand()
        )
        other = (
            other.start, other.end,
            other.chromosome.lower(), other.get_strand()
        )
        return this == other

    def get_start(self, offset=0):
        return self.start + offset

    def get_end(self, offset=0):
        return self.end + offset

    def get_chromosome(self):
        return self.chromosome

    def get_strand(self):
        return self.strand.upper()

    def get_reference_map(self):
        return self.reference_map

    def set_reference_map(self, reference_map):
        self.reference_map = reference_map


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
        verbose_name = "Wild-type sequence"
        verbose_name_plural = "Wild-type sequences"

    def __str__(self):
        return self.get_sequence()

    sequence = models.TextField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Wild-type sequence",
        validators=[validate_wildtype_sequence],
    )

    def save(self, *args, **kwargs):
        if self.sequence is not None:
            self.sequence = self.sequence.upper()
        super().save(*args, **kwargs)

    def get_sequence(self):
        return self.sequence.upper()
