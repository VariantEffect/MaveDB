
from django.contrib.auth import get_user_model
from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet

User = get_user_model()


class Serializer(object):
    """
    Base abstract class representing the functionality
    a serializer should implement. A function to serialize
    a single instance, and a function to serialize all
    instances in a queryset.
    """

    def serialize(self, pk):
        raise NotImplementedError("Method not implemented.")

    def serialize_all(self, queryset):
        raise NotImplementedError("Method not implemented.")


class ExperimentSerializer(Serializer):
    """
    An implmentation of a Serializer for an Experiment model
    """
    pass


class ExperimentSetSerializer(Serializer):
    """
    An implmentation of a Serializer for an ExperimentSet
    model
    """
    pass


class ScoreSetSerializer(Serializer):
    """
    An implmentation of a Serializer for a ScoreSet model
    """
    pass


class UserSerializer(Serializer):
    """
    An implmentation of a Serializer for a User model
    """
    pass
