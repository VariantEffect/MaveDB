from django.db import models
from django.utils.translation import ugettext_lazy as _

from core.models import TimeStampedModel

from .validators import validate_wildtype_sequence, min_start_validator


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

    annotations : :class:`models.ManyToManyField`
        A collection of annotations which map the target gene to a reference
        genome.
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
        verbose_name='Target Name'
    )

    wt_sequence = models.ForeignKey(
        to='genome.WildTypeSequence',
        blank=False,
        null=False,
        default=None,
        verbose_name='Wild Type Sequence'
    )

    annotations = models.ManyToManyField(
        to='genome.Annotation',
        blank=False,
        null=False,
        default=None,
        verbose_name='Reference Annotations'
    )

    def get_name(self):
        return self.name

    def get_target_sequence(self):
        return self.wt_sequence.get_sequence()

    def annotation_count(self):
        return self.annotations.count()

    def get_reference_genomes(self):
        genome_pks = set(a.genome.pk for a in self.annotations.all())
        return ReferenceGenome.objects.filter(pk__in=genome_pks)

    def get_primary_reference(self):
        return self.get_reference_genomes().filter(is_primary=True)

    def reference_mappings(self):
        # TODO: Refactor this to use api serialisers to avoid code duplication
        mappings = []
        for annotation in self.annotations.all():
            genome = annotation.genome
            intervals = annotation.intervals.all()

            # Serialised genome object
            genome_data = {
                'name': genome.short_name,
                'species': genome.species_name,
                'release': genome.release,
                'identifier': None if genome.ensembl_id is None else {
                    'accession': genome.ensembl_id.identifier,
                    'url': genome.ensembl_id.url
                }
            }

            # List of interval serialsations
            intervals = [
                {
                    'start': interval.start,
                    'end': interval.end,
                    'strand': interval.strand,
                    'chromosome': interval.chromosome
                }
                for interval in intervals
            ]

            mappings.append({'genome': genome_data, 'intervals': intervals})

        return mappings


class Annotation(TimeStampedModel):
    """
    Annotations define a collection of intervals within reference genome, which
    are to be used to define how a :class:`TargetGene` maps to a particular
    reference genome.

    Parameters
    ----------
    genome : :class:`models.ForeignKey`
        The genome instance this annotation refers to.

    intervals : :class:`models.ManyToManyField`
        The intervals to which a target maps to within `genome`.
    """
    class Meta:
        verbose_name = "Annotation"
        verbose_name_plural = "Annotations"

    def __str__(self):
        return 'Annotation(genome={})'.format(self.get_genome_name())

    genome = models.ForeignKey(
        to='genome.ReferenceGenome',
        blank=False,
        null=False,
        default=None,
        verbose_name='Annotation Genome'
    )

    intervals = models.ManyToManyField(
        to='genome.Interval',
        blank=False,
        verbose_name='Annotation Intervals'
    )

    def get_genome(self):
        return self.genome

    def get_genome_name(self):
        return self.genome.get_short_name()

    def get_genome_species(self):
        return self.genome.get_species_name()

    def format_genome_spcies(self):
        return self.genome.format_species_name_html()

    def get_intervals(self):
        return self.intervals.all()

    def interval_count(self):
        return self.get_intervals().count()

    def is_primary_annotation(self):
        return self.genome.is_parimary_genome()


class ReferenceGenome(TimeStampedModel):
    """
    The `ReferenceGenome` specifies fields describing a specific genome (name,
    species, identifier) along with book-keeping fields such as a URL to
    a `Ensembl` entry and a version/release descriptor.

    Parameters
    ----------
    short_name : :class:`models.CharField`
        The short name description of the genome. Example: 'hg38'.

    species_name : :class:`models.CharField`
        The species of the genome. Example: 'Homo spaiens'

    release : :class:`models.CharField`, optional, Default: None
        The database release version of the genome if applicable.

    ensembl_id : :class:`models.ForeignKey`, optional, Default: None
        The Ensembl identifier relating to this genome.
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
        max_length=256
    )

    species_name = models.CharField(
        blank=False,
        null=False,
        default=None,
        verbose_name='Species',
        max_length=256
    )

    ensembl_id = models.ForeignKey(
        to='metadata.EnsemblIdentifier',
        blank=True,
        null=True,
        default=None,
        verbose_name='Ensemble Identifier'
    )

    is_primary = models.BooleanField(
        blank=False,
        null=False,
        default=None,
    )

    def get_identifier_url(self):
        if self.ensembl_id is not None:
            return self.ensembl_id.url
        return None

    def get_identifier(self):
        if self.ensembl_id is not None:
            return self.ensembl_id.identifier
        return None

    def get_short_name(self):
        return self.short_name.lower()

    def get_species_name(self):
        return self.species_name

    def format_species_name_html(self):
        split = self.species_name.split(' ')
        if len(split) > 1:
            return "<i>{} {}</i>".format(
                split[0].capitalize(), ' '.join(split[1:]))
        else:
            return "<i>{}</i>".format(self.species_name.capitalize())

    def is_primary_genome(self):
        return self.is_primary


class Interval(TimeStampedModel):
    """
    Represents a specific region within the reference genome, including
    chromosome and strand. All intervals use 1-based indexing.

    Parameters
    ----------
    start : :class:`models.PositiveIntegerField`
        The starting base position within a reference genome (inclusive).

    end : :class:`models.PositiveIntegerField`
        The ending base position within a reference genome (inclusive).

    chromosome : :class:`models.PositiveIntegerField`
        The chromosome number this interval is one.

    strand : :class:`models.CharField, choices: {'F', 'R'}
        The strand this interval is defined with respect to.
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
            'chromosome={chr}, strand={strand}'.format(
                start=self.get_start(), end=self.get_end(),
                chr=self.get_chromosome(), strand=self.get_strand()
            )
        )

    start = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Interval start',
        validators=[min_start_validator]
    )
    end = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Interval end (inclusive)'
    )
    chromosome = models.PositiveIntegerField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Chromosome number'
    )
    strand = models.CharField(
        default=None,
        null=False,
        blank=False,
        verbose_name='Strand',
        choices=STRAND_CHOICES
    )

    def get_start(self, offset=0):
        return self.start + offset

    def get_end(self, offset=0):
        return self.end + offset

    def get_chromosome(self):
        return self.chromosome

    def get_strand(self):
        return self.strand.upper()


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
        verbose_name="Wild type sequence",
        validators=[validate_wildtype_sequence],
    )

    def get_sequence(self):
        return self.sequence.upper()
