from rest_framework import serializers

from .models import Licence


class LicenceSerializer(serializers.ModelSerializer):
    """
    Serialisers all fields of a :class:`Licence` excluding `id` and
    timestamp fields.
    """
    class Meta:
        model = Licence
        fields = ('long_name', 'short_name', 'legal_code', 'link', 'version')
        read_only_fields = fields
        write_only_fields = ()