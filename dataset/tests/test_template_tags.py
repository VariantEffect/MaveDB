from django.test import TestCase

from accounts.factories import UserFactory

from ..factories import ExperimentWithScoresetFactory
from ..templatetags import dataset_tags


class TestDisplayTargetsTag(TestCase):
    def test_shows_targets_from_public_scoresets(self):
        exp = ExperimentWithScoresetFactory()
        exp.scoresets.first().publish()
        user = UserFactory()
        result = dataset_tags.display_targets(exp, user)
        self.assertIn(exp.scoresets.first().get_target().get_name(), result)

    def test_hides_targets_from_private_scoresets(self):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        result = dataset_tags.display_targets(exp, user)
        self.assertNotIn(exp.scoresets.first().get_target().get_name(), result)

    def test_shows_targets_from_private_if_user_is_contributor(self):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        exp.scoresets.first().add_viewers(user)
        result = dataset_tags.display_targets(exp, user)
        self.assertIn(exp.scoresets.first().get_target().get_name(), result)


class TestDisplaySpeciesTag(TestCase):
    def test_shows_species_from_public_scoresets(self):
        exp = ExperimentWithScoresetFactory()
        exp.scoresets.first().publish()
        user = UserFactory()
        result = dataset_tags.display_species(exp, user)
        self.assertIn(
            list(exp.scoresets.first().get_display_target_organisms())[0],
            result
        )

    def test_hides_species_from_private_scoresets(self):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        result = dataset_tags.display_species(exp, user)
        self.assertNotIn(
            list(exp.scoresets.first().get_display_target_organisms())[0],
            result
        )

    def test_shows_species_from_private_if_user_is_contributor(self):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        exp.scoresets.first().add_viewers(user)
        result = dataset_tags.display_species(exp, user)
        self.assertIn(
            list(exp.scoresets.first().get_display_target_organisms())[0],
            result
        )


class TestVisibleChildren(TestCase):
    def test_hides_private_when_user_not_contrib(self):
        exp = ExperimentWithScoresetFactory()
        result = dataset_tags.visible_children(exp, UserFactory())
        self.assertEqual(len(result), 0)

    def test_shows_private_when_user_is_contrib(self):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        exp.children.first().add_viewers(user)
        result = dataset_tags.visible_children(exp, user)
        self.assertEqual(len(result), 1)

    def test_shows_public(self):
        exp = ExperimentWithScoresetFactory()
        exp.children.first().publish()
        result = dataset_tags.visible_children(exp, UserFactory())
        self.assertEqual(len(result), 1)
