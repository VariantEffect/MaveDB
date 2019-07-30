from rest_framework import serializers

from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializers a :class:`User` instance
    """

    display_name = serializers.CharField(source="profile.get_display_name")
    experimentsets = serializers.SerializerMethodField()
    experiments = serializers.SerializerMethodField()
    scoresets = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "username",
            "last_name",
            "first_name",
            "display_name",
            "experimentsets",
            "experiments",
            "scoresets",
        )
        read_only_fields = fields
        lookup_field = "username"

    def get_datasets(self, obj, attr, public_attr):
        user = self.context.get("user", None)
        if user is None:
            return [i.urn for i in getattr(obj.profile, public_attr)()]
        return [
            i.urn
            for i in getattr(obj.profile, attr)()
            if (not i.private) or (i.private and user in i.contributors)
        ]

    def get_experimentsets(self, obj):
        return self.get_datasets(
            obj,
            "contributor_experimentsets",
            "public_contributor_experimentsets",
        )

    def get_experiments(self, obj):
        return self.get_datasets(
            obj, "contributor_experiments", "public_contributor_experiments"
        )

    def get_scoresets(self, obj):
        return self.get_datasets(
            obj, "contributor_scoresets", "public_contributor_scoresets"
        )
