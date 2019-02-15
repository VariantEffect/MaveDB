import json

from django.test import TestCase, mock

from accounts.factories import UserFactory

from genome.factories import TargetGeneFactory, WildTypeSequenceFactory, \
    ReferenceGenomeFactory, ReferenceMapFactory

from metadata.factories import PubmedIdentifierFactory, GenomeIdentifierFactory

from ..factories import ExperimentWithScoresetFactory, ExperimentFactory, ScoreSetFactory
from ..templatetags import dataset_tags

from ..utilities import publish_dataset


class TestGroupByTarget(TestCase):
    @staticmethod
    def mock_scoresets():
        scoreset1 = ScoreSetFactory()
        target1 = TargetGeneFactory(
            name='BRCA1',
            wt_sequence=WildTypeSequenceFactory(sequence='ATCG'),
            category='Protein coding',
            scoreset=scoreset1,
        )
        ReferenceMapFactory(target=target1, genome=ReferenceGenomeFactory(
            short_name='hg38',
            organism_name='A',
            genome_id=GenomeIdentifierFactory(identifier='GCF_000146045.2')
        ))
    
        scoreset2 = ScoreSetFactory()
        target2 = TargetGeneFactory(
            name='BRCA1',
            wt_sequence=WildTypeSequenceFactory(sequence='ATCG'),
            category='Protein coding',
            scoreset=scoreset2,
        )
        ReferenceMapFactory(target=target2, genome=ReferenceGenomeFactory(
            short_name='hg38',
            organism_name='A',
            genome_id=GenomeIdentifierFactory(identifier='GCF_000146045.2')
        ))
        
        return scoreset1, scoreset2
    
    def test_returns_unique_targets_based_on_hash(self):
        s1, s2 = self.mock_scoresets()
        result = dataset_tags.group_targets([s1, s2])
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0][1]), 2)
        
        t2 = s2.get_target()
        t2.name='BRCA2'
        t2.save()
        result = dataset_tags.group_targets([s1, s2])
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0][1]), 1)
        self.assertEqual(len(result[1][1]), 1)

    def test_sorts_scoresets_within_target_by_urn(self):
        s1, s2 = self.mock_scoresets()
        result = dataset_tags.group_targets([s2, s1])
        self.assertEqual(len(result), 1)
        self.assertListEqual(
            [s.urn for s in result[0][1]],
            [s.urn for s in sorted([s2, s1], key=lambda s: s.urn)]
        )

class TestDisplayTargetsTag(TestCase):
    @mock.patch('dataset.templatetags.dataset_tags.visible_children', retun_value=[])
    def test_calls_visible_children_on_experiment(self, patch):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        exp.add_administrators(user)
        dataset_tags.display_targets(exp, user)
        patch.assert_called()
        
    @mock.patch('dataset.templatetags.dataset_tags.visible_children', retun_value=[])
    def test_calls_group_targets_on_experiment(self, patch):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        exp.add_administrators(user)
        dataset_tags.display_targets(exp, user)
        patch.assert_called()
        
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

    def test_formats_for_javascript(self):
        exp = ExperimentWithScoresetFactory()
        user = UserFactory()
        exp.scoresets.first().add_viewers(user)
        result = dataset_tags.display_targets(exp, user, javascript=True)
        self.assertEqual(
            result,
            json.dumps(sorted([exp.scoresets.first().get_target().get_name()]))
        )
        
    def test_formats_for_javascript_when_no_targets_found(self):
        exp = ExperimentFactory()
        user = UserFactory()
        result = dataset_tags.display_targets(exp, user, javascript=True)
        self.assertEqual(result, json.dumps(['-']))
        
    def test_returns_categories_for_each_target_if_categories_is_true(self):
        exp = ExperimentWithScoresetFactory()
        publish_dataset(exp.scoresets.first())
        user = UserFactory()
        result = dataset_tags.display_targets(exp, user, categories=True)
        self.assertIn(exp.scoresets.first().get_target().category, result)
        
    def test_returns_organisms_for_each_target_if_organisms_is_true(self):
        exp = ExperimentWithScoresetFactory()
        publish_dataset(exp.scoresets.first())
        user = UserFactory()
        result = dataset_tags.display_targets(exp, user, organisms=True)
        self.assertIn(
            exp.scoresets.first().get_target()
                .get_primary_reference_map()
                .format_reference_genome_organism_html(), result
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
        instance.pubmed_ids.add(pm1)
        instance.pubmed_ids.add(pm2)
        instance.children.first().pubmed_ids.add(pm2)
        instance.children.first().pubmed_ids.add(pm3)
        
        pmids = dataset_tags.parent_references(instance.children.first())
        self.assertEqual(len(pmids), 1)
        self.assertEqual(pmids[0], pm1)


class TestUrnNameFormatTag(TestCase):
    def test_adds_private_if_user_is_contributor(self):
        user = UserFactory()
        instance = ExperimentWithScoresetFactory()
        instance.add_administrators(user)
        self.assertIn(
            '[Private]',
            dataset_tags.format_urn_name_for_user(instance, user)
        )
        
    def test_does_not_add_private_if_user_is_not_contributor(self):
        user = UserFactory()
        instance = ExperimentWithScoresetFactory()
        self.assertNotIn(
            '[Private]',
            dataset_tags.format_urn_name_for_user(instance, user)
        )
        
    def test_does_not_add_private_public_instance(self):
        user = UserFactory()
        instance = ExperimentWithScoresetFactory()
        instance.add_administrators(user)
        publish_dataset(instance)
        self.assertIn(
            '[Private]',
            dataset_tags.format_urn_name_for_user(instance, user)
        )
        