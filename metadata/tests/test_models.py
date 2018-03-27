from django.db import IntegrityError
from django.test import TestCase

from dataset.models import Experiment, ScoreSet

from ..models import Keyword, DoiIdentifier, SraIdentifier, PubmedIdentifier


class TestKeyword(TestCase):

    def setUp(self):
        self.exp_1 = Experiment.objects.create(
            target="brca1",
            wt_sequence="ATCG")
        self.exp_2 = Experiment.objects.create(
            target="brca2",
            wt_sequence="ATCG")

    def test_cannot_create_duplicates(self):
        Keyword.objects.create(text="keyword 1")
        with self.assertRaises(IntegrityError):
            Keyword.objects.create(text="keyword 1")

    def test_cannot_create_with_null_text(self):
        with self.assertRaises(IntegrityError):
            Keyword.objects.create(text=None)

    def test_can_associate_multiple_keywords_with_dataset(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        kw2 = Keyword.objects.create(text="keyword 2")

        self.exp_1.keywords.add(kw1)
        self.exp_1.keywords.add(kw2)
        self.exp_1.save()

        self.assertEqual(
            list(self.exp_1.keywords.order_by('text')),
            [kw1, kw2]
        )

    def test_can_associate_keyword_with_multiple_datasets(self):
        kw1 = Keyword.objects.create(text="keyword 1")

        self.exp_1.keywords.add(kw1)
        self.exp_2.keywords.add(kw1)
        self.exp_1.save()
        self.exp_2.save()

        self.assertEqual(
            list(self.exp_1.keywords.order_by('-text')),
            list(self.exp_2.keywords.order_by('-text')),
        )

    def test_cant_add_duplicate_keywords_to_dataset(self):
        kw1 = Keyword.objects.create(text="keyword 1")

        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()

        self.assertEqual(self.exp_1.keywords.count(), 1)

    def test_delete_experiment_doesnt_delete_dataset(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        self.exp_1.delete()
        self.assertEqual(Keyword.objects.count(), 1)

    def test_delete_keyword_doesnt_delete_dataset(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        kw1.delete()
        self.assertEqual(Experiment.objects.count(), 2)
        self.assertEqual(self.exp_1.keywords.count(), 0)


class TestDoiIdentifierModel(TestCase):
    pass


class TestSraIdentidier(TestCase):
    pass


class TestPubmedIdentifier(TestCase):
    pass