from rest_framework import serializers

from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializers a :class:`User` instance
    """
    display_name = serializers.CharField(source='profile.get_display_name')
    contributor_experimentsets = serializers.StringRelatedField(
        source='profile.public_contributor_experimentsets', many=True)
    contributor_experiments = serializers.StringRelatedField(
        source='profile.public_contributor_experiments', many=True)
    contributor_scoresets = serializers.StringRelatedField(
        source='profile.public_contributor_scoresets', many=True)

    class Meta:
        model = User
        fields = (
            'username', 'last_name', 'first_name', 'display_name',
            'contributor_experimentsets', 'contributor_experiments',
            'contributor_scoresets'
        )
        read_only_fields = fields
        lookup_field = 'username'
