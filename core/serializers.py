from rest_framework import serializers

from .models import TimeStampedModel


class TimeStampedModelSerializer(serializers.ModelSerializer):
    """
    Serializes the :class:`TimeStampedModel` class fields `creation_date`
    and `modification_date`
    """

    class Meta:
        model = TimeStampedModel
        fields = ('creation_date', 'modification_date',)
