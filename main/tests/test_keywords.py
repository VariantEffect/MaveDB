
from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from main.models import Keyword, TargetOrganism, ExternalAccession
from main.models import ReferenceMapping
from experiment.models import Experiment
from scoreset.models import ScoreSet


class TestKeyword(TestCase):

    def setUp(self):
        self.exp_1 = Experiment.objects.create(
            target="brca1", wt_sequence="ATCG"
        )
        self.exp_2 = Experiment.objects.create(
            target="brca2", wt_sequence="ATCG"
        )

    def test_cannot_create_duplicates(self):
        Keyword.objects.create(text="keyword 1")
        with self.assertRaises(IntegrityError):
            Keyword.objects.create(text="keyword 1")

    # -------------------- Experiment ------------------------------ #
    def test_can_associate_multiple_keywords_with_experiment(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        kw2 = Keyword.objects.create(text="keyword 2")

        self.exp_1.keywords.add(kw1)
        self.exp_1.keywords.add(kw2)
        self.exp_1.save()

        self.assertEqual(
            list(self.exp_1.keywords.order_by('text')),
            [kw1, kw2]
        )

    def test_can_associate_keyword_with_multiple_experiments(self):
        kw1 = Keyword.objects.create(text="keyword 1")

        self.exp_1.keywords.add(kw1)
        self.exp_2.keywords.add(kw1)
        self.exp_1.save()
        self.exp_2.save()

        self.assertEqual(
            list(self.exp_1.keywords.order_by('-text')),
            list(self.exp_2.keywords.order_by('-text')),
        )

    def test_cant_add_duplicate_keywords_to_experiment(self):
        kw1 = Keyword.objects.create(text="keyword 1")

        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()

        self.assertEqual(self.exp_1.keywords.count(), 1)

    def test_delete_experiment_doesnt_delete_keyword(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        self.exp_1.delete()
        self.assertEqual(Keyword.objects.count(), 1)

    def test_delete_keyword_doesnt_delete_experiment(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        self.exp_1.keywords.add(kw1)
        self.exp_1.save()
        kw1.delete()
        self.assertEqual(Experiment.objects.count(), 2)

    # -------------------- ScoreSet ------------------------------ #
    def test_can_associate_multiple_keywords_with_scoreset(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        kw2 = Keyword.objects.create(text="keyword 2")

        scs = ScoreSet.objects.create(experiment=self.exp_1)
        scs.keywords.add(kw1)
        scs.keywords.add(kw2)
        scs.save()
        self.assertEqual(list(scs.keywords.order_by('text')), [kw1, kw2])

    def test_can_associate_keyword_with_multiple_scoresets(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        scs_2 = ScoreSet.objects.create(experiment=self.exp_2)
        scs_1.keywords.add(kw1)
        scs_2.keywords.add(kw1)
        scs_1.save()
        scs_2.save()

        self.assertEqual(
            list(scs_1.keywords.order_by('-text')),
            list(scs_2.keywords.order_by('-text')),
        )

    def test_cant_add_duplicate_keywords_to_scoreset(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        scs_1.keywords.add(kw1)
        scs_1.save()
        scs_1.keywords.add(kw1)
        scs_1.save()

        self.assertEqual(scs_1.keywords.count(), 1)

    def test_delete_scoreset_doesnt_delete_keyword(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        scs_1.keywords.add(kw1)
        scs_1.save()
        scs_1.delete()
        self.assertEqual(Keyword.objects.count(), 1)

    def test_delete_keyword_doesnt_delete_scoreset(self):
        kw1 = Keyword.objects.create(text="keyword 1")
        scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        scs_1.keywords.add(kw1)
        scs_1.save()
        kw1.delete()
        self.assertEqual(ScoreSet.objects.count(), 1)


class TestExternalAccession(TestCase):

    def setUp(self):
        self.exp_1 = Experiment.objects.create(
            target="brca1", wt_sequence="ATCG"
        )
        self.exp_2 = Experiment.objects.create(
            target="brca2", wt_sequence="ATCG"
        )

    def test_cannot_create_duplicates(self):
        ExternalAccession.objects.create(text="acc 1")
        with self.assertRaises(IntegrityError):
            ExternalAccession.objects.create(text="acc 1")

    def test_can_associate_multiple_accessions_with_experiment(self):
        obj1 = ExternalAccession.objects.create(text="acc 1")
        obj2 = ExternalAccession.objects.create(text="acc 2")

        self.exp_1.external_accessions.add(obj1)
        self.exp_1.external_accessions.add(obj2)
        self.exp_1.save()

        self.assertEqual(
            list(self.exp_1.external_accessions.order_by('text')), [obj1, obj2]
        )

    def test_can_associate_accessions_with_multiple_experiments(self):
        obj1 = ExternalAccession.objects.create(text="acc 1")

        self.exp_1.external_accessions.add(obj1)
        self.exp_2.external_accessions.add(obj1)
        self.exp_1.save()
        self.exp_2.save()

        self.assertEqual(
            list(self.exp_1.external_accessions.order_by('-text')),
            list(self.exp_2.external_accessions.order_by('-text')),
        )

    def test_cant_add_duplicate_accessions_to_experiment(self):
        obj1 = ExternalAccession.objects.create(text="acc 1")

        self.exp_1.external_accessions.add(obj1)
        self.exp_1.save()
        self.exp_1.external_accessions.add(obj1)
        self.exp_1.save()

        self.assertEqual(self.exp_1.external_accessions.count(), 1)

    def test_delete_experiment_doesnt_delete_accessions(self):
        obj1 = ExternalAccession.objects.create(text="acc 1")
        self.exp_1.external_accessions.add(obj1)
        self.exp_1.save()
        self.exp_1.delete()
        self.assertEqual(ExternalAccession.objects.count(), 1)

    def test_delete_accessions_doesnt_delete_experiment(self):
        obj1 = ExternalAccession.objects.create(text="acc 1")
        self.exp_1.external_accessions.add(obj1)
        self.exp_1.save()
        obj1.delete()
        self.assertEqual(Experiment.objects.count(), 2)


class TestTargetOrganism(TestCase):

    def setUp(self):
        self.exp_1 = Experiment.objects.create(
            target="brca1", wt_sequence="ATCG"
        )
        self.exp_2 = Experiment.objects.create(
            target="brca2", wt_sequence="ATCG"
        )

    def test_cannot_create_duplicates(self):
        TargetOrganism.objects.create(text="hsa")
        with self.assertRaises(IntegrityError):
            TargetOrganism.objects.create(text="hsa")

    def test_can_associate_multiple_accessions_with_experiment(self):
        obj1 = TargetOrganism.objects.create(text="hsa")
        obj2 = TargetOrganism.objects.create(text="mus")

        self.exp_1.target_organism.add(obj1)
        self.exp_1.target_organism.add(obj2)
        self.exp_1.save()

        self.assertEqual(
            list(self.exp_1.target_organism.order_by('text')), [obj1, obj2]
        )

    def test_can_associate_accessions_with_multiple_experiments(self):
        obj1 = TargetOrganism.objects.create(text="hsa")

        self.exp_1.target_organism.add(obj1)
        self.exp_2.target_organism.add(obj1)
        self.exp_1.save()
        self.exp_2.save()

        self.assertEqual(
            list(self.exp_1.target_organism.order_by('-text')),
            list(self.exp_2.target_organism.order_by('-text')),
        )

    def test_cant_add_duplicate_accessions_to_experiment(self):
        obj1 = TargetOrganism.objects.create(text="hsa")

        self.exp_1.target_organism.add(obj1)
        self.exp_1.save()
        self.exp_1.target_organism.add(obj1)
        self.exp_1.save()

        self.assertEqual(self.exp_1.target_organism.count(), 1)

    def test_delete_experiment_doesnt_delete_accessions(self):
        obj1 = TargetOrganism.objects.create(text="hsa")
        self.exp_1.target_organism.add(obj1)
        self.exp_1.save()
        self.exp_1.delete()
        self.assertEqual(TargetOrganism.objects.count(), 1)

    def test_delete_accessions_doesnt_delete_experiment(self):
        obj1 = TargetOrganism.objects.create(text="hsa")
        self.exp_1.target_organism.add(obj1)
        self.exp_1.save()
        obj1.delete()
        self.assertEqual(Experiment.objects.count(), 2)


class TestReferenceMapping(TestCase):

    def setUp(self):
        self.exp_1 = Experiment.objects.create(
            target="brca1", wt_sequence="ATCG"
        )
        self.exp_2 = Experiment.objects.create(
            target="brca2", wt_sequence="ATCG"
        )

    def test_can_create_and_save_minimal_mapping(self):
        mapping = ReferenceMapping.objects.create(
            reference="some gene", experiment=self.exp_1,
            target_start=0, target_end=10,
            reference_start=1990, reference_end=3450
        )
        self.assertEqual(ReferenceMapping.objects.count(), 1)

    def test_can_create_duplicate_mappings(self):
        mapping_1 = ReferenceMapping.objects.create(
            reference="some gene", experiment=self.exp_1,
            target_start=0, target_end=10,
            reference_start=1990, reference_end=3450
        )
        mapping_2 = ReferenceMapping.objects.create(
            reference="some gene", experiment=self.exp_1,
            target_start=0, target_end=10,
            reference_start=1990, reference_end=3450
        )
        self.assertEqual(ReferenceMapping.objects.count(), 2)
        m1, m2 = list(self.exp_1.referencemapping_set.all())
        self.assertEqual(m1.datahash, m2.datahash)

    def test_cannot_have_negative_target_start(self):
        with self.assertRaises(IntegrityError):
            ReferenceMapping.objects.create(
                reference="some gene", experiment=self.exp_1,
                target_start=-1, target_end=10,
                reference_start=1000, reference_end=3450
            )

    def test_cannot_have_negative_target_end(self):
        with self.assertRaises(IntegrityError):
            ReferenceMapping.objects.create(
                reference="some gene", experiment=self.exp_1,
                target_start=0, target_end=-1,
                reference_start=1000, reference_end=3450
            )

    def test_cannot_have_negative_reference_start(self):
        with self.assertRaises(IntegrityError):
            ReferenceMapping.objects.create(
                reference="some gene", experiment=self.exp_1,
                target_start=0, target_end=10,
                reference_start=-1000, reference_end=3450
            )

    def test_cannot_have_negative_reference_end(self):
        with self.assertRaises(IntegrityError):
            ReferenceMapping.objects.create(
                reference="some gene", experiment=self.exp_1,
                target_start=0, target_end=10,
                reference_start=1000, reference_end=-3450
            )
