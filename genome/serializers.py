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
    GenomicInterval,
    WildTypeSequence,
)


class ReferenceGenomeSerializer(serializers.ModelSerializer):
    """
    Serializes fields of :class:`ReferenceGenome`. Currently read only and
    will recurse on :class:`ExternalIdentifiers`.
    """
    ensembl = EnsemblIdentifierSerializer(source='ensembl_id', many=False)
    refseq = RefseqIdentifierSerializer(source='refseq_id', many=False)

    class Meta:
        model = ReferenceGenome
        fields = ('short_name', 'species_name', 'ensembl', 'refseq',)
        read_only_fields = fields

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if 'ensembl' in rep:
            rep['ensembl'].pop('offset')
        if 'refseq' in rep:
            rep['refseq'].pop('offset')
        return rep


class IntervalSerializer(serializers.ModelSerializer):
    """
    Serializes fields of :class:`GenomicInterval`. Currently read only.
    """
    class Meta:
        model = GenomicInterval
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
    uniprot = UniprotIdentifierSerializer(source='uniprot_id', many=False)
    ensembl = EnsemblIdentifierSerializer(source='refseq_id', many=False)
    refseq = RefseqIdentifierSerializer(source='refseq_id', many=False)

    class Meta:
        model = TargetGene
        depth = 2
        fields = (
            'name', 'wt_sequence', 'uniprot',
            'ensembl', 'refseq', 'reference_maps',
            'scoreset',
        )
        read_only_fields = fields
