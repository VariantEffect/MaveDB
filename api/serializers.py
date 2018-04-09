from abc import ABC, abstractmethod

from django.db.models import ObjectDoesNotExist
from django.contrib.auth import get_user_model

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet


User = get_user_model()


def add_metadata(dict_, instance):
    if isinstance(instance, ExperimentSet):
        dict_['model_type'] = instance.class_name()
    else:
        dict_['keywords'] = [kw.text for kw in instance.keywords.all()]
        dict_['doi_ids'] = {
            doi.identifier: {'url': doi.url} for doi in instance.doi_ids.all()
        }
        dict_['sra_ids'] = {
            sra.identifier: {'url': sra.url} for sra in instance.doi_ids.all()
        }
        dict_['pm_ids'] = {
            pm.identifier: {'url': pm.url} for pm in instance.pmid_ids.all()
        }
        dict_['model_type'] = instance.class_name()
    return dict_


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

        dict_ = {
            "urn": instance.urn,
            "contributors": instance.format_using_username(
                group='editors', string=False),
            "experiments": [
                e.urn for e in instance.experiments.all()
                if not (e.private and filter_private)
            ]
        }
        return add_metadata(dict_, instance)

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

        dict_ = {
            "urn": instance.urn,
            "wt_sequence": instance.get_wt_sequence(),
            "target": instance.get_target_name(),
            "target_organism": instance.get_target_organism_name(),
            "contributors": instance.format_using_username(
                group='editors', string=False),
            "experimentset": instance.experimentset.urn,
            "scoresets": [
                s.current_version.urn
                for s in instance.scoresets.all()
                if not (s.private and filter_private)
            ]
        }
        return add_metadata(dict_, instance)

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

        next_version = instance.next_version
        next_version = None if not next_version else next_version.urn

        previous_version = instance.previous_version
        previous_version = None if not previous_version else previous_version.urn

        dict_ = {
            "urn": instance.urn,
            "contributors": instance.format_using_username(
                group='editors', string=False),
            "next_version": next_version,
            "previous_version": previous_version,
            "licence": [
                instance.licence.short_name,
                instance.licence.link,
            ],
            "current_version": instance.current_version.urn,
            "score_columns": instance.score_columns,
            "count_columns": instance.count_columns
        }
        return add_metadata(dict_, instance)

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
