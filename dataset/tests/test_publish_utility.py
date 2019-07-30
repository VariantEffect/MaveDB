import datetime

from django.test import TestCase

from accounts.factories import UserFactory

from variant.factories import VariantFactory

from ..factories import (
    ExperimentSetFactory,
    ExperimentFactory,
    ScoreSetFactory,
)

from dataset.utilities import publish_dataset


class TestPublishDataset(TestCase):
    def test_publish_experimentset_sets_private_to_false(self):
        obj = ExperimentSetFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)

    def test_publish_experiment_sets_private_to_false(self):
        obj = ExperimentFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)

    def test_publish_scoreset_sets_private_to_false(self):
        obj = ScoreSetFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)

    def test_publish_experimentset_creates_public_urn(self):
        obj = ExperimentSetFactory()
        obj = publish_dataset(obj)
        self.assertTrue(obj.has_public_urn)

    def test_publish_experiment_creates_public_urn(self):
        obj = ExperimentFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)
        self.assertTrue(obj.has_public_urn)

    def test_publish_scoreset_creates_public_urn(self):
        obj = ScoreSetFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)
        self.assertTrue(obj.has_public_urn)

    def test_publish_scoreset_propagates_to_parents(self):
        obj = ScoreSetFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.parent.private)
        self.assertTrue(obj.parent.has_public_urn)

        self.assertFalse(obj.parent.parent.private)
        self.assertTrue(obj.parent.parent.has_public_urn)

    def test_publishes_variants(self):
        obj = ScoreSetFactory()
        VariantFactory(scoreset=obj)
        obj = publish_dataset(obj)
        self.assertTrue(obj.children.first().has_public_urn)

    def test_sets_user(self):
        user = UserFactory()
        obj = ScoreSetFactory()
        VariantFactory(scoreset=obj)
        obj = publish_dataset(obj, user)
        self.assertEqual(obj.modified_by, user)
        self.assertEqual(obj.parent.modified_by, user)
        self.assertEqual(obj.parent.parent.modified_by, user)

    def test_sets_publish_date(self):
        obj = ScoreSetFactory()
        VariantFactory(scoreset=obj)
        obj = publish_dataset(obj)
        self.assertEqual(obj.publish_date, datetime.date.today())
        self.assertEqual(obj.parent.publish_date, datetime.date.today())
        self.assertEqual(obj.parent.parent.publish_date, datetime.date.today())

    def test_does_not_publish_twice(self):
        obj = ExperimentSetFactory()
        obj = publish_dataset(obj)
        obj = publish_dataset(obj)
        self.assertEqual(publish_dataset(obj).urn, publish_dataset(obj).urn)

    def test_can_publish_sequential_with_same_parent(self):
        obj1 = ScoreSetFactory()
        obj2 = ScoreSetFactory(experiment=obj1.parent)
        obj1 = publish_dataset(obj1)
        obj2 = publish_dataset(obj2)
        self.assertNotEqual(
            publish_dataset(obj1).urn, publish_dataset(obj2).urn
        )

    def test_publish_scoreset_sequential_values_assigned_to_variants(self):
        obj1 = ScoreSetFactory()
        v1 = VariantFactory(scoreset=obj1)
        v2 = VariantFactory(scoreset=obj1)
        publish_dataset(obj1)
        v1.refresh_from_db()
        v2.refresh_from_db()
        self.assertNotEqual(v1.urn[-1], v2.urn[-1])

    def test_typeerror_not_a_dataset(self):
        with self.assertRaises(TypeError):
            publish_dataset(VariantFactory())
