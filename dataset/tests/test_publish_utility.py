import datetime

from django.test import TestCase
from django.contrib.auth.models import Group

from accounts.factories import UserFactory

from variant.factories import VariantFactory

from ..factories import (
    ExperimentSetFactory,
    ExperimentFactory,
    ScoreSetFactory,
)

from dataset.utilities import publish_dataset


class TestPublishDataset(TestCase):
    def test_publishes_experimentset(self):
        obj = ExperimentSetFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)
        self.assertTrue(obj.has_public_urn)

    def test_publishes_experiment(self):
        obj = ExperimentFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)
        self.assertTrue(obj.has_public_urn)

    def test_publishes_scoreset(self):
        obj = ScoreSetFactory()
        obj = publish_dataset(obj)
        self.assertFalse(obj.private)
        self.assertTrue(obj.has_public_urn)

    def test_publishes_scoreset_propagates(self):
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
        first_urn = obj.urn
        obj = publish_dataset(obj)
        second_urn = obj.urn
        self.assertEqual(first_urn, second_urn)
