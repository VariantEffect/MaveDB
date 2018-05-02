import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.factories import UserFactory

from dataset.factories import ExperimentSetFactory, ScoreSetFactory
from metadata.factories import (
    KeywordFactory, DoiIdentifierFactory, SraIdentifierFactory,
    PubmedIdentifierFactory
)

User = get_user_model()


class TestDatasetModel(TestCase):

    def test_save_updates_modification_date(self):
        instance = ExperimentSetFactory()
        time_now = datetime.date.today()
        instance.save()
        self.assertEqual(instance.modification_date, time_now)

    def test_set_created_by_sets_updates_created_by_and_time_stamps(self):
        user = UserFactory()
        instance = ExperimentSetFactory()
        instance.set_created_by(user)
        instance.save()
        self.assertEqual(instance.created_by, user)
        self.assertEqual(instance.creation_date, datetime.date.today())

    def test_publish_sets_private_to_false_and_sets_publish_date(self):
        instance = ExperimentSetFactory()
        instance.publish()
        instance.save()
        self.assertEqual(instance.private, False)
        self.assertEqual(instance.publish_date, datetime.date.today())

    def test_approve_sets_approved_to_true(self):
        instance = ExperimentSetFactory()
        instance.approve()
        instance.save()
        self.assertEqual(instance.approved, True)

    def test_typeerror_add_non_keyword_instance(self):
        instance = ExperimentSetFactory()
        with self.assertRaises(TypeError):
            instance.add_keyword('')

        # instance.add_keyword(KeywordFactory())
        self.assertEqual(instance.keywords.count(), 1)

    def test_typeerror_add_non_external_identifier_instance(self):
        instance = ExperimentSetFactory()
        with self.assertRaises(TypeError):
            instance.add_identifier(KeywordFactory())

        # instance.add_identifier(DoiIdentifierFactory())
        self.assertEqual(instance.doi_ids.count(), 1)

    def test_clear_m2m_clears_m2m_relationships(self):
        instance = ExperimentSetFactory()
        # instance.add_identifier(DoiIdentifierFactory())
        # instance.add_identifier(SraIdentifierFactory())
        # instance.add_identifier(PubmedIdentifierFactory())

        self.assertEqual(instance.doi_ids.count(), 1)
        instance.doi_ids.clear()
        self.assertEqual(instance.doi_ids.count(), 0)

        self.assertEqual(instance.sra_ids.count(), 1)
        instance.sra_ids.clear()
        self.assertEqual(instance.sra_ids.count(), 0)

        self.assertEqual(instance.pubmed_ids.count(), 1)
        instance.pubmed_ids.clear()
        self.assertEqual(instance.pubmed_ids.count(), 0)

    def test_propagate_set_value_propagates_to_parents(self):
        instance = ScoreSetFactory()
        instance.propagate_set_value('private', False)

        self.assertFalse(instance.private)
        self.assertFalse(instance.experiment.private)
        self.assertFalse(instance.experiment.experimentset.private)

    def test_save_can_propagate(self):
        instance = ScoreSetFactory()
        instance.propagate_set_value('private', True)
        instance.save(save_parents=True)

        instance.propagate_set_value('private', False)
        instance.save(save_parents=False)

        # Only scoreset should change since we return parent to their
        # original data without saving.
        instance.refresh_from_db()
        instance.experiment.refresh_from_db()
        instance.experiment.experimentset.refresh_from_db()
        self.assertFalse(instance.private)
        self.assertTrue(instance.experiment.private)
        self.assertTrue(instance.experiment.experimentset.private)

        instance.propagate_set_value('private', False)
        instance.save(save_parents=True)

        instance.refresh_from_db()
        instance.experiment.refresh_from_db()
        instance.experiment.experimentset.refresh_from_db()
        self.assertFalse(instance.private)
        self.assertFalse(instance.experiment.private)
        self.assertFalse(instance.experiment.experimentset.private)


