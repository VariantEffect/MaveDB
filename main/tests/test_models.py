
from django.test import TestCase
from django.db import IntegrityError

from main.models import TargetOrganism
from main.models import ReferenceMapping
from dataset.models import Experiment


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
