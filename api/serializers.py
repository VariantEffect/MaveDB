from abc import ABC, abstractmethod

from django.db.models import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet

from accounts.permissions import user_is_anonymous

User = get_user_model()


class Serializer(ABC):
    """
    Base abstract class representing the functionality
    a serializer should implement. A function to serialize
    a single instance, and a function to serialize all
    instances in a queryset.
    """

    @abstractmethod
    def serialize(self, pk):
        pass

    @abstractmethod
    def serialize_set(self, queryset):
        pass


class ExperimentSetSerializer(Serializer):
    """
    An implmentation of a Serializer for an ExperimentSet
    model
    """

    def serialize(self, pk):
        try:
            instance = ExperimentSet.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return {}

        return {
            "accession": instance.accession,
            "authors": instance.get_authors_by_username(string=False),
            "experiments": [
                e.accession for e in instance.experiment_set.all()
            ]
        }

    def serialize_set(self, queryset):
        return {
            "experimentsets": [self.serialize(exps.pk) for exps in queryset]
        }


class ExperimentSerializer(Serializer):
    """
    An implmentation of a Serializer for an Experiment model
    """

    def serialize(self, pk):
        try:
            instance = Experiment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return {}

        return {
            "accession": instance.accession,
            "authors": instance.get_authors_by_username(string=False),
            "experimentset": instance.experimentset.accession,
            "scoresets": [
                s.get_latest_version().accession
                for s in instance.scoreset_set.all()
            ]
        }

    def serialize_set(self, queryset):
        return {
            "experiments": [self.serialize(exp.pk) for exp in queryset]
        }


class ScoreSetSerializer(Serializer):
    """
    An implmentation of a Serializer for a ScoreSet model
    """

    def serialize(self, pk):
        try:
            instance = ScoreSet.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return {}

        replaced_by = instance.get_replaced_by()
        replaces = instance.replaces
        replaced_by = '' if not replaced_by else replaced_by.accession
        replaces = '' if not replaces else replaces.accession

        return {
            "accession": instance.accession,
            "authors": instance.get_authors_by_username(string=False),
            "replaced_by": replaced_by,
            "replaces": replaces,
            "reviewed": instance.approved,
            "current_version": instance.get_latest_version().accession,
            "score_columns": instance.scores_columns,
            "count_columns": instance.counts_columns
        }

    def serialize_set(self, queryset):
        return {
            "scoresets": [self.serialize(s.pk) for s in queryset]
        }


class UserSerializer(Serializer):
    """
    An implmentation of a Serializer for a User model
    """

    def serialize(self, pk, filter_private=True):
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return {}

        profile = user.profile
        return {
            "username": user.username,
            "experimentsets": [
                i.accession for i in profile.administrator_experimentsets()
                if not (i.private and filter_private)
            ],
            "experiments": [
                i.accession for i in profile.administrator_experiments()
                if not (i.private and filter_private)
            ],
            "scoresets": [
                i.accession for i in profile.administrator_scoresets()
                if not (i.private and filter_private)
            ]
        }

    def serialize_set(self, queryset, filter_private=True):
        return {
            "users": [self.serialize(s.pk, filter_private) for s in queryset]
        }
