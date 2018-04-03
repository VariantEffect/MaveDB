from django.db import IntegrityError
from django.test import TestCase

from dataset.factories import ExperimentFactory

from ..models import Keyword, DoiIdentifier, SraIdentifier, PubmedIdentifier
from ..factories import (
    KeywordFactory, DoiIdentifierFactory,
    PubmedIdentifierFactory, SraIdentifierFactory
)


class TestKeyword(TestCase):

    def setUp(self):
        self.exp_1 = ExperimentFactory()
        self.exp_2 = ExperimentFactory()

    def test_cannot_create_duplicates(self):
        keyword = KeywordFactory()
        with self.assertRaises(IntegrityError):
            KeywordFactory(text=keyword.text)

    def test_cannot_create_with_null_text(self):
        with self.assertRaises(IntegrityError):
            KeywordFactory(text=None)

    def test_can_associate_multiple_keywords_with_dataset(self):
        kw1 = KeywordFactory()
        kw2 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.keywords.add(kw2)
        self.assertEqual(self.exp_1.keywords.count(), 2)

    def test_can_associate_keyword_with_multiple_datasets(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_2.keywords.add(kw1)
        self.assertEqual(self.exp_1.keywords.count(), 1)
        self.assertEqual(self.exp_2.keywords.count(), 1)

    def test_cant_add_duplicate_keywords_to_dataset(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.keywords.add(kw1)
        self.assertEqual(self.exp_1.keywords.count(), 1)

    def test_delete_experiment_doesnt_delete_kw(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.delete()
        self.assertEqual(Keyword.objects.count(), 1)

    def test_deleted_keyword_removed_from_experiment_keywords(self):
        kw1 = KeywordFactory()
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        self.exp_1.refresh_from_db()
        self.assertEqual(self.exp_1.keywords.count(), 1)

        kw1.delete()
        self.exp_1.save()
        self.exp_1.refresh_from_db()
        self.assertEqual(self.exp_1.keywords.count(), 0)


class TestDoiIdentifierModel(TestCase):
    pass


class TestSraIdentidier(TestCase):
    pass


class TestPubmedIdentifier(TestCase):
    pass