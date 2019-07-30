from rest_framework import serializers

from .models import (
    ExternalIdentifier,
    SraIdentifier,
    DoiIdentifier,
    PubmedIdentifier,
    UniprotIdentifier,
    EnsemblIdentifier,
    RefseqIdentifier,
    Keyword,
    AnnotationOffset,
    UniprotOffset,
    EnsemblOffset,
    RefseqOffset,
    GenomeIdentifier,
)


class KeywordSerializer(serializers.ModelSerializer):
    """
    Serializes the `text` field of a Keyword.
    """

    class Meta:
        model = Keyword
        fields = ("text",)


# Offsets
# --------------------------------------------------------------------------- #
class AnnotationOffsetSerializer(serializers.ModelSerializer):
    """
    Serializes the `offset` field of an :class:`AnnotationOffset` subclass.
    """

    class Meta:
        model = AnnotationOffset
        fields = ("offset",)
        read_only_fields = fields


class UniprotOffsetSerializer(serializers.ModelSerializer):
    """
    Serializes the `offset` field of an :class:`UniprotOffset`.
    """

    class Meta(AnnotationOffsetSerializer.Meta):
        model = UniprotOffset

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance:
            serializer = UniprotIdentifierSerializer()
            identifier_rep = serializer.to_representation(
                instance=instance.identifier
            )
            representation.update(identifier_rep)
            return representation
        return representation


class EnsemblOffsetSerializer(serializers.ModelSerializer):
    """
    Serializes the `offset` field of an :class:`EnsemblOffset`.
    """

    class Meta(AnnotationOffsetSerializer.Meta):
        model = EnsemblOffset

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance:
            serializer = EnsemblIdentifierSerializer()
            identifier_rep = serializer.to_representation(
                instance=instance.identifier
            )
            representation.update(identifier_rep)
            return representation
        return representation


class RefseqOffsetSerializer(serializers.ModelSerializer):
    """
    Serializes the `offset` field of an :class:`RefseqIdentifier.
    """

    class Meta(AnnotationOffsetSerializer.Meta):
        model = RefseqOffset

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance:
            serializer = RefseqIdentifierSerializer()
            identifier_rep = serializer.to_representation(
                instance=instance.identifier
            )
            representation.update(identifier_rep)
            return representation
        return representation


# ExternalIdentifiers
# --------------------------------------------------------------------------- #
class ExternalIdentifierSerializer(serializers.ModelSerializer):
    """
    Serializes the `url` and `identifier` fields of an
    :class:`ExternalIdentifier subclass.
    """

    class Meta:
        model = ExternalIdentifier
        fields = ("identifier", "url", "dbversion", "dbname")


class SraIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`SraIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = SraIdentifier


class DoiIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`DoiIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = DoiIdentifier


class PubmedIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`PubmedIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = PubmedIdentifier


class GenomeIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`PubmedIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = GenomeIdentifier


# Annotation based
# --------------------------------------------------------------------------- #
class EnsemblIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`EnsemblIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = EnsemblIdentifier


class RefseqIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`RefseqIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = RefseqIdentifier


class UniprotIdentifierSerializer(ExternalIdentifierSerializer):
    """
    Serializes a :class:`UniprotIdentifier` instance/queryset.
    """

    class Meta(ExternalIdentifierSerializer.Meta):
        model = UniprotIdentifier
