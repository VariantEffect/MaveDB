import datetime

from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.shortcuts import reverse

from core.utilities import base_url

from ..models.experimentset import ExperimentSet
from ..factories import ExperimentSetFactory, ExperimentFactory


class TestExperimentSet(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ExperimentSet`, representing an experiment with associated
    :py:class:`Experiment` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """
    def test_new_experiment_is_assigned_all_permission_groups(self):
        self.assertEqual(Group.objects.count(), 0)
        _ = ExperimentSetFactory()
        self.assertEqual(Group.objects.count(), 3)

    def test_deleted_experiment_deletes_all_permission_groups(self):
        obj = ExperimentSetFactory()
        self.assertEqual(Group.objects.count(), 3)
        obj.delete()
        self.assertEqual(Group.objects.count(), 0)

    def test_publish_updates_published_and_modification_dates(self):
        exps = ExperimentSetFactory()
        exps.publish()
        self.assertEqual(exps.publish_date, datetime.date.today())
        self.assertEqual(exps.modification_date, datetime.date.today())

    def test_publish_updates_private_to_false(self):
        exps = ExperimentSetFactory()
        exps.publish()
        self.assertFalse(exps.private)

    def test_autoassign_does_not_reassign_deleted_urn(self):
        exps1 = ExperimentSetFactory()
        exps1.publish()
        previous = exps1.urn
        exps1.delete()
        exps2 = ExperimentSetFactory()
        exps2.publish()
        self.assertGreater(exps2.urn, previous)

    def test_cannot_create_experimentsets_with_duplicate_urn(self):
        obj = ExperimentSetFactory()
        with self.assertRaises(IntegrityError):
            ExperimentSetFactory(urn=obj.urn)

    def test_experimentset_not_approved_and_private_by_default(self):
        obj = ExperimentSet()
        self.assertFalse(obj.approved)
        self.assertTrue(obj.private)

    def test_cannot_delete_experimentset_with_experiments(self):
        exp = ExperimentFactory()
        with self.assertRaises(ProtectedError):
            exp.experimentset.delete()

    def test_publish_twice_doesnt_change_urn(self):
        exps = ExperimentSetFactory()
        exps.publish()
        exps.refresh_from_db()
        old_urn = exps.urn
        self.assertTrue(exps.has_public_urn)

        exps = ExperimentSet.objects.first()
        exps.publish()
        exps.refresh_from_db()
        new_urn = exps.urn

        self.assertTrue(exps.has_public_urn)
        self.assertEqual(new_urn, old_urn)

    def test_can_assign_perma_urns_in_order_in_atomic_transaction(self):
        with transaction.atomic():
            instance1 = ExperimentSet(private=False)
            instance2 = ExperimentSet(private=False)
            
            instance1.save()
            self.assertIn('1', instance1.urn)
            
            instance2.save()
            self.assertIn('2', instance2.urn)

    def test_can_get_url(self):
        obj = ExperimentSetFactory()
        self.assertEqual(
            obj.get_url(),
            base_url() + reverse('dataset:experimentset_detail', args=(obj.urn,))
        )