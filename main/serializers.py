from rest_framework import serializers

from .models import Licence, SiteInformation


class LicenceSerializer(serializers.ModelSerializer):
    """
    Serialisers all fields of a :class:`Licence` excluding `id` and
    timestamp fields.
    """
    class Meta:
        model = Licence
        fields = ('long_name', 'short_name', 'link', 'version')
        read_only_fields = fields
        write_only_fields = ()


class SiteInformationSerializer(serializers.ModelSerializer):
    """Serializes all fields in SiteInformation"""
    class Meta:
        model = SiteInformation
        fields = '__all__'