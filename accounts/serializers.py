from rest_framework import serializers

from django.contrib.auth import get_user_model

User = get_user_model()

# TODO: Authenticated users should be able to see private children in parent instances


class UserSerializer(serializers.ModelSerializer):
    """
    Serializers a :class:`User` instance
    """
    display_name = serializers.CharField(source='profile.get_display_name')
    experimentsets = serializers.StringRelatedField(
        source='profile.public_contributor_experimentsets', many=True)
    experiments = serializers.StringRelatedField(
        source='profile.public_contributor_experiments', many=True)
    scoresets = serializers.StringRelatedField(
        source='profile.public_contributor_scoresets', many=True)

    class Meta:
        model = User
        fields = (
            'username', 'last_name', 'first_name', 'display_name',
            'experimentsets', 'experiments', 'scoresets'
        )
        read_only_fields = fields
        lookup_field = 'username'
