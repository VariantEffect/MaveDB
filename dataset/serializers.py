from rest_framework import serializers

from core.serializers import TimeStampedModelSerializer
from genome.serializers import TargetGeneSerializer
from metadata.serializers import (
    KeywordSerializer, SraIdentifierSerializer,
    DoiIdentifierSerializer, PubmedIdentifierSerializer
)

from .models.base import DatasetModel
from .models.experimentset import ExperimentSet
from .models.experiment import Experiment
from .models.scoreset import ScoreSet


class DatasetModelSerializer(TimeStampedModelSerializer):

    keywords = KeywordSerializer(many=True)
    sra_ids = SraIdentifierSerializer(many=True)
    doi_ids = DoiIdentifierSerializer(many=True)
    pubmed_ids = PubmedIdentifierSerializer(many=True)

    class Meta(TimeStampedModelSerializer.Meta):
        model = DatasetModel
        fields = TimeStampedModelSerializer.Meta.fields + (
            'urn', 'publish_date', 'created_by', 'modified_by', 'private',
            'extra_metadata', 'abstract_text', 'method_text',
            'short_description', 'title', 'keywords', 'sra_ids', 'doi_ids',
            'pubmed_ids',
        )
        read_only_fields = fields
        write_only_fields = ()


class ScoreSetSerializer(DatasetModelSerializer):

    target = TargetGeneSerializer(many=False)
    experiment = serializers.StringRelatedField(many=False)

    score_columns = serializers.ListSerializer(child=serializers.CharField())
    count_columns = serializers.ListSerializer(child=serializers.CharField())
    metadata_columns = serializers.ListSerializer(child=serializers.CharField())

    previous_version = serializers.StringRelatedField(many=False)
    next_version = serializers.StringRelatedField(many=False)
    current_version = serializers.StringRelatedField(many=False)

    class Meta(DatasetModelSerializer.Meta):
        model = ScoreSet
        fields = DatasetModelSerializer.Meta.fields + (
            'licence', 'target', 'score_columns', 'count_columns',
            'metadata_columns', 'previous_version', 'next_version',
            'current_version', 'variant_count', 'experiment',
        )


class ExperimentSerializer(DatasetModelSerializer):
    scoresets = serializers.StringRelatedField(many=True)
    experimentset = serializers.StringRelatedField(many=False)

    class Meta(DatasetModelSerializer.Meta):
        model = Experiment
        fields = DatasetModelSerializer.Meta.fields + (
            'scoresets', 'experimentset',
        )


class ExperimentSetSerializer(DatasetModelSerializer):
    experiments = serializers.StringRelatedField(many=True)

    class Meta(DatasetModelSerializer.Meta):
        model = ExperimentSet
        fields = DatasetModelSerializer.Meta.fields + (
            'experiments',
        )
