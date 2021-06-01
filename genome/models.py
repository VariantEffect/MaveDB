from typing import Optional, Any

from django.db import models

from core.models import TimeStampedModel

from .validators import (
    validate_wildtype_sequence,
    min_start_validator,
    validate_gene_name,
    validate_genome_short_name,
    validate_organism_name,
    validate_strand,
    validate_chromosome,
    min_end_validator,
    sequence_is_protein,
    sequence_is_dna,
)


class TargetGene(TimeStampedModel):
    """
    Models a target gene, defining the wild-type sequence, a free-text name
    and a collection of reference_maps relating the gene to reference genomes,
    which can be from different organism.

    The fields `wt_sequence` and `scoreset` are allowed
    to be saved as `None` to allow complex form handling but this *should*
    be transient within the view-validate-commit form upload loop.

    Parameters
    ----------
    name : `models.CharField`
        The name of the target gene.

    category : `models.CharField`
        Protein coding, regulatory or other

    wt_sequence : `models.OneToOneField`
        An instance of :class:`WildTypeSequence` defining the wildtype sequence
        of this target gene.

    scoreset : `models.OneToOneField`
        One to one relationship associating this target with a scoreset. If
        this scoreset is deleted, the target and associated reference_maps/intervals
        will also be deleted.

    refseq_id : `models.ForeignKeyField`
        Related RefSeq identifier

    uniprot_id : `models.ForeignKeyField`
        Related UniProt identifier

    ensembl_id : `models.ForeignKeyField`
        Related Ensembl identifier
    """

    CATEGORY_CHOICES = (
        ("Protein coding", "Protein coding"),
        ("Regulatory", "Regulatory"),
        ("Other noncoding", "Other noncoding"),
    )

    class Meta:
        ordering = ("name",)
        verbose_name = "Target Gene"
        verbose_name_plural = "Target Genes"

    @classmethod
    def tracked_fields(cls):
        return ("name", "wt_sequence", "scoreset_id", "wt", "category")

    def __str__(self):
        return self.get_name()

    name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name="Target name",
        max_length=256,
        validators=[validate_gene_name],
    )
    category = models.CharField(
        blank=False,
        null=False,
        default="Protein coding",
        verbose_name="Target type",
        max_length=32,
        choices=CATEGORY_CHOICES,
    )

    scoreset = models.OneToOneField(
        to="dataset.ScoreSet",
        on_delete=models.CASCADE,
        null=False,
        default=None,
        blank=False,
        related_name="target",
    )

    wt_sequence = models.OneToOneField(
        to="genome.WildTypeSequence",
        blank=False,
        null=False,
        default=None,
        verbose_name="Reference sequence",
        related_name="target",
        on_delete=models.PROTECT,
    )

    # External Identifiers
    # ----------------------------------------------------------------------- #
    uniprot_id = models.ForeignKey(
        to="metadata.UniprotIdentifier",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name="associated_%(class)ss",
    )
    ensembl_id = models.ForeignKey(
        to="metadata.EnsemblIdentifier",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name="associated_%(class)ss",
    )
    refseq_id = models.ForeignKey(
        to="metadata.RefseqIdentifier",
        on_delete=models.SET_NULL,
        null=True,
        default=None,
        blank=True,
        related_name="associated_%(class)ss",
    )

    def delete(self, using=None, keep_parents=False):
        retval = super().delete(using, keep_parents)
        self.wt_sequence.delete()
        return retval

    def get_name(self) -> str:
        return self.name

    def get_unique_name(self) -> str:
        """Target name appended to its scoreset urn."""
        return "{} | {}".format(self.name, self.get_scoreset_urn())

    def get_scoreset(self):
        if hasattr(self, "scoreset"):
            return self.scoreset
        return None

    def get_scoreset_urn(self) -> Optional[str]:
        if self.get_scoreset():
            return self.scoreset.urn
        return None

    def get_wt_sequence_string(self) -> Optional[str]:
        if self.wt_sequence:
            return self.wt_sequence.get_sequence()
        return None

    def get_wt_sequence(self) -> Optional["WildTypeSequence"]:
        if hasattr(self, "wt_sequence"):
            return self.wt_sequence
        return None

    def set_wt_sequence(self, sequence: "WildTypeSequence"):
        if not isinstance(sequence, WildTypeSequence):
            raise TypeError(
                "Found {}, expected {} or str.".format(
                    type(sequence).__name__, WildTypeSequence.__name__
                )
            )
        self.wt_sequence = sequence

    def match_sequence(self, sequence: Optional[str]) -> bool:
        this = (self.get_wt_sequence_string() or "").lower()
        other = (sequence or "").lower()
        return this == other

    def get_offset_annotation(self, related_field) -> Optional[Any]:
        value = getattr(self, related_field, None)
        if value is not None:
            return value.first()
        return None

    def get_uniprot_offset_annotation(self):
        return self.get_offset_annotation("uniprotoffset")

    def get_ensembl_offset_annotation(self):
        return self.get_offset_annotation("ensembloffset")

    def get_refseq_offset_annotation(self):
        return self.get_offset_annotation("refseqoffset")

    def reference_map_count(self):
        return self.reference_maps.count()

    def get_reference_maps(self):
        return self.reference_maps.all()

    def get_primary_reference_map(self):
        return self.reference_maps.filter(is_primary=True).first()

    def get_reference_genomes(self):
        genome_pks = set(a.genome.pk for a in self.get_reference_maps())
        return ReferenceGenome.objects.filter(pk__in=genome_pks)

    def equals(self, other):
        return self.hash() == other.hash()

    def hash(self):
        genome = getattr(self.get_primary_reference_map(), "genome", None)
        # Fallback to other reference maps
        if genome is None:
            genome = getattr(self.get_reference_maps().first(), "genome", None)
        # Every reference map should have a genome by database constraint.
        # Set as null values in case.
        if genome is None:
            genome = ("", "", "")
        else:
            genome = (
                genome.short_name,
                genome.organism_name,
                getattr(genome.genome_id, "identifier", ""),
            )
        repr_ = str(
            (self.name, self.wt_sequence.sequence, self.category) + genome
        )
        return hash(repr_)


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
        return "ReferenceMap(genome={}, primary={})".format(
            self.get_reference_genome_name(), self.is_primary_reference_map()
        )

    genome = models.ForeignKey(
        to="genome.ReferenceGenome",
        blank=False,
        null=False,
        default=None,
        on_delete=models.PROTECT,
        verbose_name="Reference genome",
        related_name="associated_reference_maps",
    )

    target = models.ForeignKey(
        to="genome.TargetGene",
        blank=False,
        null=False,
        default=None,
        verbose_name="Target",
        related_name="reference_maps",
        on_delete=models.CASCADE,
    )

    is_primary = models.BooleanField(
        blank=True, null=False, default=False, verbose_name="Primary"
    )

    def get_target(self):
        if hasattr(self, "target"):
            return self.target
        return None

    def set_target(self, target):
        if not isinstance(target, TargetGene):
            raise TypeError(
                "Found {}, expected {}.".format(
                    type(target).__name__, TargetGene.__name__
                )
            )
        self.target = target

    def get_reference_genome(self):
        return self.genome

    def set_reference_genome(self, genome):
        if not isinstance(genome, ReferenceGenome):
            raise TypeError(
                "Found {}, expected {}.".format(
                    type(genome).__name__, ReferenceGenome.__name__
                )
            )
        self.genome = genome

    def get_reference_genome_name(self):
        if self.get_reference_genome():
            return self.get_reference_genome().get_short_name()

    def get_reference_genome_organism(self):
        if self.get_reference_genome():
            return self.get_reference_genome().get_organism_name()

    def format_reference_genome_organism_html(self):
        """
        Return a HTML string formatting the associated genomes organism name
        using italics and capitalisation.
        """
        if self.get_reference_genome():
            return self.get_reference_genome().format_organism_name_html()

    def get_intervals(self):
        return self.intervals.all()

    def set_is_primary(self, primary=True):
        self.is_primary = primary

    def is_primary_reference_map(self):
        return self.is_primary


class ReferenceGenome(TimeStampedModel):
    """
    The :class:`ReferenceGenome` specifies fields describing a specific genome
    in terms of a short name, organism and various external identifiers.

    Parameters
    ----------
    short_name : `CharField`
        The short name description of the genome. Example: 'hg38'.

    organism_name : `CharField`
        The organism of the genome. Example: 'Homo sapiens'

    ensembl_id : `ForeignKey`
        An :class:`EnsemblIdentifier` instance to relating to this genome.

    refseq_id : `ForeignKey`
        A :class:`RefseqIdentifier` instance to relating to this genome.
    """

    class Meta:
        ordering = ("id",)
        verbose_name = "Reference genome"
        verbose_name_plural = "Reference genomes"

    def __str__(self):
        return self.get_short_name()

    short_name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name="Name",
        max_length=256,
        validators=[validate_genome_short_name],
    )
    organism_name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name="Organism",
        max_length=256,
        validators=[validate_organism_name],
    )

    # Potential ExternalIdentifiers that may be linked.
    genome_id = models.ForeignKey(
        to="metadata.GenomeIdentifier",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name="Genome assembly identifier",
        related_name="associated_%(class)ss",
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
        return "{} | {}".format(
            self.get_short_name(), self.get_organism_name()
        )

    def get_short_name(self):
        return self.short_name

    def get_organism_name(self):
        return self.organism_name

    def format_organism_name_html(self):
        """
        Return a HTML string formatting the associated genomes organism name
        using italics and capitalisation.
        """
        return "<i>{}</i>".format(self.get_organism_name().capitalize())


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
        ("+", "+"),  # (database value, verbose value used in UI)
        ("-", "-"),
    )

    class Meta:
        ordering = ["start"]
        verbose_name = "Reference interval"
        verbose_name_plural = "Reference intervals"

    def __str__(self):
        return (
            "GenomicInterval(start={start}, end={end}, "
            "chromosome={chr}, strand={strand})".format(
                start=self.get_start(),
                end=self.get_end(),
                chr=self.get_chromosome(),
                strand=self.get_strand(),
            )
        )

    start = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name="Start",
        validators=[min_start_validator],
    )
    end = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name="End (inclusive)",
        validators=[min_end_validator],
    )
    chromosome = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name="Chromosome identifier",
        max_length=32,
        validators=[validate_chromosome],
    )
    strand = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name="Strand",
        choices=STRAND_CHOICES,
        max_length=1,
        validators=[validate_strand],
    )
    reference_map = models.ForeignKey(
        to="genome.ReferenceMap",
        default=None,
        blank=False,
        null=None,
        on_delete=models.CASCADE,
        related_name="intervals",
    )

    # Don't overload the __eq__ for Django models. This might break Django
    # internals for forms/views etc.
    def equals(self, other):
        """
        Compares two intervals based on `start`, `end`, lowercase `chromosome`
        and `strand`.
        """
        this = (
            self.start,
            self.end,
            self.chromosome.lower(),
            self.get_strand(),
        )
        other = (
            other.start,
            other.end,
            other.chromosome.lower(),
            other.get_strand(),
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

    sequence_type : `models.CharField`
        Protein sequence (amino acids) or DNA (nucleotides)
    """

    class SequenceType:
        DNA = "dna"
        PROTEIN = "protein"
        INFER = "infer"

        @classmethod
        def detect_sequence_type(cls, sequence):
            if sequence_is_dna(sequence):
                return cls.DNA
            elif sequence_is_protein(sequence):
                return cls.PROTEIN
            else:
                raise ValueError(
                    f"Unknown sequence '{sequence}'. It is not protein or DNA."
                )

        @classmethod
        def is_protein(cls, value):
            return value == cls.PROTEIN

        @classmethod
        def is_dna(cls, value):
            return value == cls.DNA

        @classmethod
        def choices(cls):
            return [
                (cls.INFER, "Infer"),
                (cls.DNA, "DNA"),
                (cls.PROTEIN, "Protein"),
            ]

    class Meta:
        verbose_name = "Reference sequence"
        verbose_name_plural = "Reference sequences"

    def __str__(self):
        return self.get_sequence()

    sequence = models.TextField(
        default=None,
        blank=False,
        null=False,
        verbose_name="Reference sequence",
        validators=[validate_wildtype_sequence],
    )
    sequence_type = models.CharField(
        blank=True,
        null=False,
        default=SequenceType.INFER,
        verbose_name="Reference sequence type",
        max_length=32,
        choices=SequenceType.choices(),
    )

    @property
    def is_dna(self):
        return self.__class__.SequenceType.is_dna(self.sequence_type)

    @property
    def is_protein(self):
        return self.__class__.SequenceType.is_protein(self.sequence_type)

    def save(self, *args, **kwargs):
        if self.sequence is not None:
            self.sequence = self.sequence.upper()
            self.sequence_type = (
                (
                    self.__class__.SequenceType.detect_sequence_type(
                        self.sequence
                    )
                )
                if self.__class__.SequenceType.INFER
                else self.sequence_type
            )

        return super().save(*args, **kwargs)

    def get_sequence(self):
        return self.sequence.upper()

    def is_attached(self):
        return getattr(self, "target", None) is not None
