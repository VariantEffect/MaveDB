from rest_framework import serializers

from .models import Variant
from dataset.serializers import (
    ScoreSetSerializer,
)


class VariantSerializer(serializers.ModelSerializer):
    """
    Serializes the :class:`Variant` and class fields:

    urn : `str`, optional.
    hgvs_nt : `str`, required.
    hgvs_splice : `str`, required.
    hgvs_pro : `str`, required.
    scoreset : `ScoreSet`, required.
    data : `JSONField`
    """

    scoreset = ScoreSetSerializer(many=False)

    class Meta:
        model = Variant
        fields = ("urn", "hgvs_nt", "hgvs_splice", "hgvs_pro", "scoreset", "data")
        read_only_fields = fields
        lookup_field = "urn"
