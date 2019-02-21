import datetime

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.factories import UserFactory

from dataset import models
from dataset.templatetags.dataset_tags import visible_children
from dataset.factories import ExperimentSetFactory, ScoreSetFactory, \
    ExperimentFactory

User = get_user_model()


class TestDatasetModel(TestCase):

    def test_save_updates_modification_date(self):
        instance = ExperimentSetFactory()
        time_now = datetime.date.today()
        instance.save()
        self.assertEqual(instance.modification_date, time_now)

    def test_set_modified_by(self):
        user = UserFactory()
        instance = ExperimentSetFactory()
        instance.set_modified_by(user)
        instance.save()
        self.assertEqual(instance.modified_by, user)

    def test_set_created_by(self):
        user = UserFactory()
        instance = ExperimentSetFactory()
        instance.set_created_by(user)
        instance.save()
        self.assertEqual(instance.created_by, user)

    def test_set_publish_date(self):
        instance = ExperimentSetFactory()
        instance.set_publish_date(datetime.date.today())
        instance.save()
        self.assertEqual(instance.publish_date, datetime.date.today())

    def test_clear_m2m_clears_m2m_relationships(self):
        instance = ExperimentSetFactory()

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

    def test_transaction_rolls_back_if_exception(self):
        try:
            with transaction.atomic():
                ScoreSetFactory()
                raise AttributeError()
        except AttributeError:
            self.assertEqual(models.scoreset.ScoreSet.objects.count(), 0)
            self.assertEqual(models.experiment.Experiment.objects.count(), 0)
            self.assertEqual(models.experimentset.ExperimentSet.objects.count(), 0)
            
    def test_children_for_user_excludes_private_if_not_contributor(self):
        private_instance = ExperimentFactory()
        user = UserFactory()
        
        public_instance = ExperimentFactory(
            experimentset=private_instance.experimentset)
        public_instance.private = False
        public_instance.save()
        
        result = visible_children(private_instance.experimentset, user)
        self.assertNotIn(private_instance, result)
        self.assertIn(public_instance, result)
        
    def test_children_for_user_includes_private_if_contributor(self):
        user = UserFactory()
        private_instance = ExperimentFactory()
        private_instance.add_viewers(user)
        
        public_instance = ExperimentFactory(
            experimentset=private_instance.experimentset)
        public_instance.private = False
        public_instance.save()
        
        result = visible_children(private_instance.experimentset, user)
        self.assertIn(private_instance, result)
        self.assertIn(public_instance, result)
        
    def test_children_for_exclude_private_user_is_none(self):
        private_instance = ExperimentFactory()

        public_instance = ExperimentFactory(
            experimentset=private_instance.experimentset)
        public_instance.private = False
        public_instance.save()

        result = visible_children(private_instance.experimentset, None)
        self.assertNotIn(private_instance, result)
        self.assertIn(public_instance, result)

    def test_parent_for_user_none_if_parent_is_none(self):
        instance = ExperimentSetFactory()
        self.assertIsNone(instance.parent_for_user())
    
    def test_parent_for_user_returns_parent_if_public(self):
        parent = ExperimentSetFactory(private=False)
        instance = ExperimentFactory(experimentset=parent)
        self.assertIs(parent, instance.parent_for_user())
    
    def test_parent_for_user_returns_none_if_private_and_user_not_contributor(self):
        parent = ExperimentSetFactory(private=True)
        instance = ExperimentFactory(experimentset=parent)
        user = UserFactory()
        self.assertIsNone(instance.parent_for_user(user))
    
    def test_parent_for_user_returns_if_private_and_user_is_contributor(self):
        parent = ExperimentSetFactory(private=True)
        instance = ExperimentFactory(experimentset=parent)
        user = UserFactory()
        parent.add_viewers(user)
        self.assertIs(parent, instance.parent_for_user(user))
