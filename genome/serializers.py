from rest_framework import serializers

from metadata.serializers import (
    UniprotIdentifierSerializer,
    EnsemblIdentifierSerializer,
    RefseqIdentifierSerializer,
)

from genome.models import (
    TargetGene,
    ReferenceMap,
    ReferenceGenome,
    Interval,
    WildTypeSequence,
)


class ReferenceGenomeSerializer(serializers.ModelSerializer):
    """
    Serializes fields of :class:`ReferenceGenome`. Currently read only and
    will recurse on :class:`ExternalIdentifiers`.
    """
    ensembl_id = EnsemblIdentifierSerializer(many=False)
    refseq_id = RefseqIdentifierSerializer(many=False)

    class Meta:
        model = ReferenceGenome
        fields = ('short_name', 'species_name', 'ensembl_id', 'refseq_id',)
        read_only_fields = fields


class IntervalSerializer(serializers.ModelSerializer):
    """
    Serializes fields of :class:`Interval`. Currently read only.
    """
    class Meta:
        model = Interval
        fields = ('start', 'end', 'chromosome', 'strand',)
        read_only_fields = fields


class WildTypeSequenceSerializer(serializers.ModelSerializer):
    """
    Serializes `sequence` field of :class:`WildTypeSequence`.
    """
    class Meta:
        model = WildTypeSequence
        fields = ('sequence',)
        read_only_fields = fields


class ReferenceMapSerializer(serializers.ModelSerializer):
    """
    Serializes :class:`ReferenceMap` where `intervals` are returned as
    a recursively serialised list of json objects.
    """
    intervals = IntervalSerializer(many=True)
    genome = ReferenceGenomeSerializer(many=False)

    class Meta:
        model = ReferenceMap
        fields = ('genome', 'is_primary', 'intervals',)
        read_only_fields = ('genome', 'is_primary', 'intervals',)


class TargetGeneSerializer(serializers.ModelSerializer):
    """
    Serializes the :class:`TargetGene` but will not recurse on the `scoreset`
    field using the string representation (urn) instead.
    """
    scoreset = serializers.StringRelatedField(many=False)
    reference_maps = ReferenceMapSerializer(many=True)
    wt_sequence = WildTypeSequenceSerializer(many=False)
    uniprot_id = UniprotIdentifierSerializer(many=False)
    ensembl_id = EnsemblIdentifierSerializer(many=False)
    refseq_id = RefseqIdentifierSerializer(many=False)

    class Meta:
        model = TargetGene
        depth = 2
        fields = (
            'name', 'wt_sequence', 'uniprot_id',
            'ensembl_id', 'refseq_id', 'reference_maps',
            'scoreset',
        )
        read_only_fields = fields
