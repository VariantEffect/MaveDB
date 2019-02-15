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
        
    @staticmethod
    def stringify_instance(instance):
        if instance is None:
            return None
        return instance.urn
    

class ScoreSetSerializer(DatasetModelSerializer):

    target = TargetGeneSerializer(many=False)
    experiment = serializers.SerializerMethodField()

    score_columns = serializers.ListSerializer(child=serializers.CharField())
    count_columns = serializers.ListSerializer(child=serializers.CharField())

    # Defaults to 'get_<field_name>'. Raises error if you try to be redundant.
    previous_version = serializers.SerializerMethodField()
    next_version = serializers.SerializerMethodField()
    current_version = serializers.SerializerMethodField()
    
    def get_experiment(self, obj):
        return self.stringify_instance(
            obj.parent_for_user(self.context.get('user', None)))
      
    def get_previous_version(self, obj):
        user = self.context.get('user', None)
        return self.stringify_instance(obj.get_previous_version(user))

    def get_current_version(self, obj):
        user = self.context.get('user', None)
        return self.stringify_instance(obj.get_current_version(user))
    
    def get_next_version(self, obj):
        user = self.context.get('user', None)
        return self.stringify_instance(obj.get_next_version(user))
            
    class Meta(DatasetModelSerializer.Meta):
        model = ScoreSet
        fields = DatasetModelSerializer.Meta.fields + (
            'licence', 'target', 'score_columns', 'count_columns',
            'previous_version', 'next_version',
            'current_version', 'variant_count', 'experiment',
            'data_usage_policy',
        )
        fields = tuple([f for f in fields if f != 'sra_ids'])


class ExperimentSerializer(DatasetModelSerializer):
    scoresets = serializers.SerializerMethodField('children')
    experimentset = serializers.SerializerMethodField()
    
    def get_experimentset(self, obj):
        return self.stringify_instance(
            obj.parent_for_user(self.context.get('user', None)))
    
    def children(self, obj):
        return [c.urn for c in
                obj.children_for_user(self.context.get('user', None))]

    class Meta(DatasetModelSerializer.Meta):
        model = Experiment
        fields = DatasetModelSerializer.Meta.fields + (
            'scoresets', 'experimentset',
        )


class ExperimentSetSerializer(DatasetModelSerializer):
    experiments = serializers.SerializerMethodField('children')

    def children(self, obj):
        return [c.urn for c in
                obj.children_for_user(self.context.get('user', None))]

    class Meta(DatasetModelSerializer.Meta):
        model = ExperimentSet
        fields = DatasetModelSerializer.Meta.fields + (
            'experiments',
        )
