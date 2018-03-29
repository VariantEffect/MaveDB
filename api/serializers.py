from abc import ABC, abstractmethod

from django.db.models import ObjectDoesNotExist
from django.contrib.auth import get_user_model

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet


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

    def serialize(self, pk, filter_private=True):
        try:
            instance = ExperimentSet.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return {}

        return {
            "urn": instance.urn,
            "contributors": instance.format_using_username(
                group='editors', string=False),
            "experiments": [
                e.urn for e in instance.experiments.all()
                if not (e.private and filter_private)
            ]
        }

    def serialize_set(self, queryset, filter_private=True):
        return {
            "experimentsets": [
                self.serialize(exps.pk, filter_private) for exps in queryset
            ]
        }


class ExperimentSerializer(Serializer):
    """
    An implmentation of a Serializer for an Experiment model
    """

    def serialize(self, pk, filter_private=True):
        try:
            instance = Experiment.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return {}

        return {
            "urn": instance.urn,
            "contributors": instance.format_using_username(
                group='editors', string=False),
            "experimentset": instance.experimentset.urn,
            "scoresets": [
                s.current_version.urn
                for s in instance.scoresets.all()
                if not (s.private and filter_private)
            ]
        }

    def serialize_set(self, queryset, filter_private=True):
        return {
            "experiments": [
                self.serialize(exp.pk, filter_private) for exp in queryset
            ]
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

        replaced_by = instance.next_version
        replaced_by = None if not replaced_by else replaced_by.urn

        replaces = instance.previous_version
        replaces = None if not replaces else replaces.urn

        return {
            "urn": instance.urn,
            "contributors": instance.format_using_username(
                group='editors', string=False),
            "replaced_by": replaced_by,
            "replaces": replaces,
            "licence": [
                instance.licence.short_name,
                instance.licence.link,
            ],
            "current_version": instance.current_version.urn,
            "score_columns": instance.score_columns,
            "count_columns": instance.count_columns
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
            "first_name": user.first_name,
            "last_name": user.last_name,
            "experimentsets": [
                i.urn for i in profile.administrator_experimentsets()
                if not (i.private and filter_private)
            ],
            "experiments": [
                i.urn for i in profile.administrator_experiments()
                if not (i.private and filter_private)
            ],
            "scoresets": [
                i.urn for i in profile.administrator_scoresets()
                if not (i.private and filter_private)
            ]
        }

    def serialize_set(self, queryset, filter_private=True):
        return {
            "users": [self.serialize(s.pk, filter_private) for s in queryset]
        }
