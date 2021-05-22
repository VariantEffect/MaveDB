from django.test import TestCase

from dataset.factories import ExperimentSetFactory

from ..factories import UserFactory
from .. import serializers


class TestUserSerializer(TestCase):
    def test_get_datasets_calls_public_attr_when_no_context_user(self):
        user = UserFactory()

        private = ExperimentSetFactory(private=True)
        public = ExperimentSetFactory(private=False)
        private.add_administrators(user)
        public.add_administrators(user)

        data = serializers.UserSerializer(user, context={"user": None}).data
        self.assertNotIn(private.urn, data["experimentsets"])
        self.assertIn(public.urn, data["experimentsets"])

    def test_get_datasets_excludes_private_instance_calling_user_is_not_contrib_for(
        self,
    ):
        user = UserFactory()
        calling_user = UserFactory()

        private = ExperimentSetFactory(private=True)
        public = ExperimentSetFactory(private=False)
        private.add_administrators(user)
        public.add_administrators(user)

        data = serializers.UserSerializer(
            user, context={"user": calling_user}
        ).data
        self.assertNotIn(private.urn, data["experimentsets"])
        self.assertIn(public.urn, data["experimentsets"])

    def test_get_datasets_includes_private_instance_calling_user_is_contrib_for(
        self,
    ):
        user = UserFactory()
        user.profile.contributor_experimentsets()
        calling_user = UserFactory()

        private = ExperimentSetFactory(private=True)
        public = ExperimentSetFactory(private=False)
        private.add_administrators(user)
        public.add_administrators(user)
        private.add_administrators(calling_user)

        data = serializers.UserSerializer(
            user, context={"user": calling_user}
        ).data
        self.assertIn(private.urn, data["experimentsets"])
        self.assertIn(public.urn, data["experimentsets"])
