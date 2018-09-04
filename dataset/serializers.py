import logging

from rest_framework import serializers

from core.serializers import TimeStampedModelSerializer

from main.serializers import LicenceSerializer
from accounts.serializers import UserSerializer

from genome.serializers import TargetGeneSerializer
from metadata.serializers import (
    KeywordSerializer, SraIdentifierSerializer,
    DoiIdentifierSerializer, PubmedIdentifierSerializer
)

from .models.base import DatasetModel
from .models.experimentset import ExperimentSet
from .models.experiment import Experiment
from .models.scoreset import ScoreSet


logger = logging.getLogger('django')


class DatasetModelSerializer(TimeStampedModelSerializer):

    keywords = KeywordSerializer(many=True)
    sra_ids = SraIdentifierSerializer(many=True)
    doi_ids = DoiIdentifierSerializer(many=True)
    pubmed_ids = PubmedIdentifierSerializer(many=True)
    contributors = UserSerializer(many=True)
    licence = LicenceSerializer(many=False)
    created_by = serializers.StringRelatedField(many=False)
    modified_by = serializers.StringRelatedField(many=False)

    class Meta(TimeStampedModelSerializer.Meta):
        model = DatasetModel
        fields = TimeStampedModelSerializer.Meta.fields + (
            'urn', 'publish_date', 'created_by', 'modified_by',
            'extra_metadata', 'abstract_text', 'method_text',
            'short_description', 'title', 'keywords', 'sra_ids', 'doi_ids',
            'pubmed_ids', 'contributors',
        )
        read_only_fields = fields
        lookup_field = 'urn'


class ScoreSetSerializer(DatasetModelSerializer):

    target = TargetGeneSerializer(many=False)
    experiment = serializers.StringRelatedField(many=False)

    score_columns = serializers.ListSerializer(child=serializers.CharField())
    count_columns = serializers.ListSerializer(child=serializers.CharField())

    previous_version = serializers.StringRelatedField(
        source="previous_public_version", many=False)
    next_version = serializers.StringRelatedField(
        source="next_public_version", many=False)
    current_version = serializers.StringRelatedField(
        source='current_public_version', many=False)

    class Meta(DatasetModelSerializer.Meta):
        model = ScoreSet
        fields = DatasetModelSerializer.Meta.fields + (
            'licence', 'target', 'score_columns', 'count_columns',
            'previous_version', 'next_version',
            'current_version', 'variant_count', 'experiment',
        )
        fields = tuple([f for f in fields if f != 'sra_ids'])


class ExperimentSerializer(DatasetModelSerializer):
    scoresets = serializers.StringRelatedField(
        source='public_scoresets', many=True)
    experimentset = serializers.StringRelatedField(many=False)

    class Meta(DatasetModelSerializer.Meta):
        model = Experiment
        fields = DatasetModelSerializer.Meta.fields + (
            'scoresets', 'experimentset',
        )


class ExperimentSetSerializer(DatasetModelSerializer):
    experiments = serializers.StringRelatedField(
        source='public_experiments', many=True)

    class Meta(DatasetModelSerializer.Meta):
        model = ExperimentSet
        fields = DatasetModelSerializer.Meta.fields + (
            'experiments',
        )
