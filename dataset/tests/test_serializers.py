from django.test import TestCase, mock

from accounts.factories import UserFactory

from .. import constants
from ..models import scoreset, experimentset, experiment
from ..factories import (
    ExperimentFactory,
    ExperimentSetFactory,
    ScoreSetFactory,
)
from ..serializers import (
    ExperimentSetSerializer,
    ExperimentSerializer,
    ScoreSetSerializer,
)


class TestExperimentSetSerializer(TestCase):
    def test_private_children_hidden_by_default(self):
        parent = ExperimentSetFactory(private=False)
        child = ExperimentFactory(experimentset=parent, private=True)
        data = ExperimentSetSerializer(parent).data
        self.assertNotIn(child.urn, data["experiments"])

    def test_private_children_shown_if_context_user_is_contributor(self):
        parent = ExperimentSetFactory(private=False)
        child = ExperimentFactory(experimentset=parent, private=True)
        user = UserFactory()
        child.add_viewers(user)
        data = ExperimentSetSerializer(parent, context={"user": user}).data
        self.assertIn(child.urn, data["experiments"])


class TestExperimentSerializer(TestCase):
    def test_private_children_hidden_by_default(self):
        parent = ExperimentFactory(private=False)
        child = ScoreSetFactory(experiment=parent, private=True)
        data = ExperimentSerializer(parent).data
        self.assertNotIn(child.urn, data["scoresets"])

    def test_private_children_shown_if_context_user_is_contributor(self):
        parent = ExperimentFactory(private=False)
        child = ScoreSetFactory(experiment=parent, private=True)
        user = UserFactory()
        child.add_viewers(user)
        data = ExperimentSerializer(parent, context={"user": user}).data
        self.assertIn(child.urn, data["scoresets"])

    @mock.patch.object(experiment.Experiment, "parent_for_user")
    def test_calls_parent_for_user_with_context_user(self, patch):
        instance = ExperimentFactory()
        user = UserFactory()
        _ = ExperimentSerializer(instance, context={"user": user}).data
        patch.assert_called_with(*(user,))


class TestScoreSetSerializer(TestCase):
    def test_columns_contains_hgvs(self):
        scs = ScoreSetFactory(private=False)
        data = ScoreSetSerializer(scs).data
        self.assertIn(constants.hgvs_nt_column, data["score_columns"])
        self.assertIn(constants.hgvs_pro_column, data["score_columns"])

        self.assertIn(constants.hgvs_nt_column, data["count_columns"])
        self.assertIn(constants.hgvs_pro_column, data["count_columns"])

    @mock.patch.object(scoreset.ScoreSet, "get_previous_version")
    def test_calls_get_previous_version_with_user(self, patch):
        instance = ScoreSetFactory()
        user = UserFactory()
        _ = ScoreSetSerializer(instance, context={"user": user}).data
        patch.assert_called_with(*(user,))

    @mock.patch.object(scoreset.ScoreSet, "get_next_version")
    def test_calls_get_next_version_with_user(self, patch):
        instance = ScoreSetFactory()
        user = UserFactory()
        _ = ScoreSetSerializer(instance, context={"user": user}).data
        patch.assert_called_with(*(user,))

    @mock.patch.object(scoreset.ScoreSet, "get_current_version")
    def test_calls_get_current_version_with_user(self, patch):
        instance = ScoreSetFactory()
        user = UserFactory()
        _ = ScoreSetSerializer(instance, context={"user": user}).data
        patch.assert_called_with(*(user,))

    @mock.patch.object(scoreset.ScoreSet, "get_previous_version")
    def test_calls_get_version_with_user_as_none(self, patch):
        instance = ScoreSetFactory()
        _ = ScoreSetSerializer(instance).data
        patch.assert_called_with(*(None,))

    @mock.patch.object(ScoreSetSerializer, "stringify_instance")
    def test_calls_stringify_on_get_version_result(self, patch):
        instance = ScoreSetFactory()
        _ = ScoreSetSerializer(instance).data
        patch.assert_called()

    @mock.patch.object(scoreset.ScoreSet, "parent_for_user")
    def test_calls_parent_for_user_with_context_user(self, patch):
        instance = ScoreSetFactory()
        user = UserFactory()
        _ = ScoreSetSerializer(instance, context={"user": user}).data
        patch.assert_called_with(*(user,))
