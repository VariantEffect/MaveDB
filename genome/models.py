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
    and a collection of annotations relating the gene to reference genomes,
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
        this scoreset is deleted, the target and associated annotations/intervals
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
        """
        Returns the string name of this target.

        Returns
        -------
        `str`
            The name of this target.
        """
        return self.name

    def get_unique_name(self):
        """
        Returns the `name` concatenated with the associated scoreset urn.
        """
        return '{} | {}'.format(self.name, self.get_scoreset_urn())

    def get_scoreset_urn(self):
        """
        Returns the URN of the associated :class:`dataset.models.scoreset.ScoreSet`
        if it exists, otherwise None.

        Returns
        -------
        `str`, optional.
            URN or None if no scoreset is attached.
        """
        if self.scoreset:
            return self.scoreset.urn

    def get_wt_sequence_string(self):
        """
        Returns the wildtype sequence of nucleotides of the associated
        :class:`WildTypeSequence` if it exists, otherwise None.

        Returns
        -------
        `str`, optional.
            Wild-type sequence string or None if no instance is attached.
        """
        if self.wt_sequence:
            return self.wt_sequence.get_sequence()

    def get_wt_sequence(self):
        """
        Returns the :class:`WildTypeSequence` instance if it exists,
        otherwise None.

        Returns
        -------
        :class:`WildTypeSequence`, optional.
            Wild-type sequence string or None if no instance is attached.
        """
        return self.wt_sequence

    def set_wt_sequence(self, sequence):
        """
        Sets the `wt_sequence` instance to `sequence`. Saving these changes
        is the responsibility of the caller.

        Parameters
        ----------
        sequence : :class:`WildTypeSequence`
            Associates this instance with the supplied :class:`WildTypeSequence`
            instance.
        """
        if not isinstance(sequence, WildTypeSequence):
            raise TypeError("Found {}, expected {} or str.".format(
                type(sequence).__name__, WildTypeSequence.__name__
            ))
        self.wt_sequence = sequence

    def annotation_count(self):
        """
        Returns the count of attached :class:`ReferenceMap` instances.

        Returns
        -------
        `int`
            Count of attached :class:`ReferenceMap` instances.
        """
        return self.annotations.count()

    def get_annotations(self):
        """
        Returns the `QuerySet` of attached :class:`ReferenceMap` instances. This
        may be empty.

        Returns
        -------
        `QuerySet`
            The set of attached :class:`ReferenceMap` instances.
        """
        return self.annotations.all()

    def get_reference_genomes(self):
        """
        Returns the :class:`ReferenceGenome` instances from the attached
        :class:`ReferenceMap` instances.

        Returns
        -------
        `QuerySet`
            A set of :class:`ReferenceGenome` instances extracted from
            any attached :class:`ReferenceMap` instances.
        """
        genome_pks = set(a.genome.pk for a in self.get_annotations())
        return ReferenceGenome.objects.filter(pk__in=genome_pks)

    def serialise(self):
        """Returns a serialised `dict` of this instance's fields. Recurses the
        serialisation for relational fields.

        The `dict` instance will have the keys:
            - `name`
            - `scoreset`
            - `wt_sequence`
            - `annotations`
            - `external_identifiers`

        Returns
        -------
        `dict`
            The serialised data of this instance.
        """
        ensembl_id = self.ensembl_id
        refseq_id = self.refseq_id
        uniprot_id = self.uniprot_id

        return {
            'name': self.name,
            'scoreset': None if not self.scoreset else self.scoreset.urn,
            'wt_sequence': self.get_wt_sequence_string(),
            'annotations': [a.serialise() for a in self.annotations.all()],
            'external_identifiers': {
                'refseq': None if not refseq_id else refseq_id.serialise(),
                'ensembl': None if not ensembl_id else ensembl_id.serialise(),
                'uniprot': None if not uniprot_id else uniprot_id.serialise()
            }
        }


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
            self.get_reference_genome_name(), self.is_primary_annotation())

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
        """
        Returns the target associated with this reference_map otherwise None.

        Returns
        -------
        :class:`TargetGene`
        """
        return self.target

    def set_target_gene(self, target):
        """
        Sets the target for this instnace. Saving changes is left as the
        responsibility of the caller.

        Parameters
        ----------
        target : :class:`TargetGene`
            Associates this instance with the supplied :class:`TargetGene`
            instance.
        """
        if not isinstance(target, TargetGene):
            raise TypeError("Found {}, expected {}.".format(
                type(target).__name__, TargetGene.__name__
            ))
        self.target = target

    def get_reference_genome(self):
        """
        Return the associated genome for this reference_map if it exists.

        Returns
        -------
        :class:`ReferenceGenome`, optional.
            The :class:`ReferenceGenome` instance if one is attached, otherwise
            `None`.
        """
        return self.genome

    def set_reference_genome(self, genome):
        """
        Set the reference genome to `genome`. Saving changes is left as the
        responsibility of the caller.

        Parameters
        ----------
        genome : :class:`ReferenceGenome`
            Associates this instance with the supplied :class:`ReferenceGenome`
            instance.
        """
        if not isinstance(genome, ReferenceGenome):
            raise TypeError("Found {}, expected {}.".format(
                type(genome).__name__, ReferenceGenome.__name__
            ))
        self.genome = genome

    def get_reference_genome_name(self):
        """
        Return the string name of genome associated with this reference_map.
        """
        if self.get_reference_genome():
            return self.get_reference_genome().get_short_name()

    def get_reference_genome_species(self):
        """
        Return the string species name of genome associated with this
        reference_map.

        Returns
        -------
        `str`, optional.
            The attached genome's species or None if there is no attached
            genome.
        """
        if self.get_reference_genome():
            return self.get_reference_genome().get_species_name()

    def format_reference_genome_species_html(self):
        """
        Return a HTML string formatting the associated genomes species name
        using italics and capitalisation.

        Returns
        -------
        `str`, optional.
            Formats the species name by enclosing captialised name if
            HTML italics tags. Use with `|safe` in templates.
        """
        if self.get_reference_genome():
            return self.get_reference_genome().format_species_name_html()

    def get_intervals(self):
        """
        Return the :class:`Interval` instances defining a mapping of
        genomic coordinates with respect to the :class:`ReferenceGenome`.

        Returns
        -------
        `QuerySet`
            The `QuerySet` of intervals attached to this instance.
        """
        return self.intervals.all()

    def set_is_primary(self, primary=True):
        """
        Sets the primary status as `primary`. Saving changes is left as the
        responsibility of the caller.
        """
        self.is_primary = primary

    def is_primary_annotation(self):
        """
        Returns True if the associated :class:`ReferenceGenome` is marked
        as primary.
        """
        return self.is_primary

    def serialise(self):
        """
        Returns a serialised `dict` of this instance's fields. Recurses the
        serialisation for relational fields.

        The `dict` instance will have the keys:
            - `primary`
            - `reference`
            - `intervals`

        Returns
        -------
        `dict`
            The serialised data of this instance.
        """
        ref_genome = self.get_reference_genome()
        return {
            'primary': self.is_primary_annotation(),
            'reference_genome': None if not ref_genome else ref_genome.serialise(),
            'intervals': [i.serialise() for i in self.get_intervals()]
        }


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
    ensembl_id = models.ForeignKey(
        to='metadata.EnsemblIdentifier',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name='Ensembl identifier',
        related_name='associated_%(class)ss',
    )
    refseq_id = models.ForeignKey(
        to='metadata.RefseqIdentifier',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name='RefSeq identifier',
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
        if self.ensembl_id is not None:
            return self.get_ensembl_id()
        elif self.refseq_id is not None:
            return self.get_refseq_id()
        return None

    def get_refseq_id(self):
        """
        Returns the :class:`RefseqIdentifier` if there is one attached,
        otherwise `None`.

        Returns
        -------
        :class:`RefseqIdentifier`, optional.
            The :class:`RefseqIdentifier` identifier if one is attached,
            otherwise None.
        """
        return self.refseq_id

    def get_ensembl_id(self):
        """
        Returns the :class:`EnsemblIdentifier` if there is one attached,
        otherwise `None`.

        Returns
        -------
        :class:`EnsemblIdentifier`, optional.
            The :class:`EnsemblIdentifier` identifier if one is attached,
            otherwise None.
        """
        return self.ensembl_id

    def get_short_name(self):
        """
        The short name identifier of this genome, usually following
        the format <species_abbreviation><version> for example 'hg37'.

        Returns
        -------
        `str`
            The short name identifier of this genome, usually following
            the format <species_abbreviation><version> for example 'hg37'.
        """
        return self.short_name

    def get_species_name(self):
        """
        The scientific name of the species this genome comes from.

        Returns
        -------
        `str`
            The scientific species name.
        """
        return self.species_name

    def format_species_name_html(self):
        """
        Return a HTML string formatting the associated genomes species name
        using italics and capitalisation.

        Returns
        -------
        `str`, optional.
            Formats the species name by enclosing captialised name if
            HTML italics tags. Use with `|safe` in templates.
        """
        return "<i>{}</i>".format(self.get_species_name().capitalize())

    def serialise(self):
        """
        Returns a serialised `dict` of this instance's fields. Recurses the
        serialisation for relational fields.

        The `dict` instance will have the keys:
            - `name`
            - `species`
            - `external_identifier`

        Returns
        -------
        `dict`
            The serialised data of this instance.
        """
        ensembl_id = self.get_ensembl_id()
        refseq_id = self.get_refseq_id()

        return {
            'short_name': self.get_short_name(),
            'species_name': self.get_species_name(),
            'external_identifiers': {
                'refseq': None if not refseq_id else refseq_id.serialise(),
                'ensembl': None if not ensembl_id else ensembl_id.serialise()
            }
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

    reference_map : `ForeignKey`
        An reference_map instance that this interval is associated with.
    """
    STRAND_CHOICES = (
        ('F', 'Forward'),  # (database value, verbose value used in UI)
        ('R', 'Reverse')
    )

    class Meta:
        ordering = ['start']
        verbose_name = "Reference interval"
        verbose_name_plural = "Reference intervals"

    def __str__(self):
        return (
            'Interval(start={start}, end={end}, ' 
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

        Parameters
        ----------
        other : :class:`Interval`
            The interval to compare this instance to.

        Returns
        -------
        `bool`
            True if the intervals are the same based on `start`, `end`,
            lowercase `chromosome` and `strand`.
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
        """
        Returns the start index added to an `offset`.

        Parameters
        ----------
        offset : `int`
            The offset to add to the starting index.

        Returns
        -------
        `int`
            The start index added to the offset.
        """
        return self.start + offset

    def get_end(self, offset=0):
        """
        Returns the end index added to an `offset`.

        Parameters
        ----------
        offset : `int`
            The offset to add to the starting index.

        Returns
        -------
        `int`
            The end index added to the offset.
        """
        return self.end + offset

    def get_chromosome(self):
        """
        Returns the chromosome identifier this interval is specified for.

        Returns
        -------
        `str`
            Returns the chromosome identifier this interval is specified for.
        """
        return self.chromosome

    def get_strand(self):
        """
        Returns the strand identifier this interval is specified for. Either
        'F' for 'Forward' and 'R' for 'Reverse'.

        Returns
        -------
        `str`
            Returns 'F' for 'Forward' and 'R' for 'Reverse'.
        """
        return self.strand.upper()

    def get_annotation(self):
        """
        Returns the :class:`ReferenceMap` this instance is attached to, otherwise
        `None`.

        Returns
        -------
        :class:`ReferenceMap`, optional.
            The :class:`ReferenceMap` this instance is attached to, otherwise
            `None`.
        """
        return self.reference_map

    def set_annotation(self, annotation):
        """
        Attaches this interval to `reference_map`. Saving is the responsibility
        of the user.

        Parameters
        ----------
        annotation : :class:`ReferenceMap`
            The :class:`Annotation` to attach this interval to.
        """
        self.reference_map = annotation

    def serialise(self):
        """
        Returns a serialised `dict` of this instance's fields.

        The `dict` instance will have the keys:
            - `start`
            - `end`
            - `chromosome`
            - `strand`

        Returns
        -------
        `dict`
            The serialised data of this instance.
        """
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
        """
        Returns the nucleotide sequence.

        Returns
        -------
        `str`
            The nucleotide sequence.
        """
        return self.sequence.upper()

    def serialise(self):
        """
        Returns a serialised `dict` of this instance's fields.

        The `dict` instance will have the keys:
            - `sequence`

        Returns
        -------
        `dict`
            The serialised data of this instance.
        """
        return {'sequence': self.get_sequence()}
