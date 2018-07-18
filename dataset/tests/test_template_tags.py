from django.test import TestCase

from accounts.factories import UserFactory

from metadata.factories import PubmedIdentifierFactory

from ..factories import ExperimentWithScoresetFactory
from ..templatetags import dataset_tags

from ..utilities import publish_dataset


class TestDisplayTargetsTag(TestCase):
    def test_shows_targets_from_public_scoresets(self):
        exp = ExperimentWithScoresetFactory()
        publish_dataset(exp.scoresets.first())
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
        publish_dataset(exp.scoresets.first())
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
        publish_dataset(exp.scoresets.first())
        result = dataset_tags.visible_children(exp, UserFactory())
        self.assertEqual(len(result), 1)


class TestParentReferences(TestCase):
    def test_excludes_duplicated_references_in_child(self):
        instance = ExperimentWithScoresetFactory()
        
        instance.pubmed_ids.clear()
        instance.children.first().pubmed_ids.clear()
        
        pm1 = PubmedIdentifierFactory(identifier="25075907")
        pm2 = PubmedIdentifierFactory(identifier="20711194")
        pm3 = PubmedIdentifierFactory(identifier="29269382")
        instance.add_identifier(pm1)
        instance.add_identifier(pm2)
        instance.children.first().add_identifier(pm2)
        instance.children.first().add_identifier(pm3)
        
        pmids = dataset_tags.parent_references(instance.children.first())
        self.assertEqual(len(pmids), 1)
        self.assertEqual(pmids[0], pm1)
