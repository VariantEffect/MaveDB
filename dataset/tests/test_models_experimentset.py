from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.shortcuts import reverse

from core.utilities import base_url

from ..models.experimentset import ExperimentSet, assign_public_urn
from ..factories import ExperimentSetFactory, ExperimentFactory
from ..utilities import publish_dataset


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

    def test_can_get_url(self):
        obj = ExperimentSetFactory()
        self.assertEqual(
            obj.get_url(),
            base_url() + reverse('dataset:experimentset_detail', args=(obj.urn,))
        )


class TestAssignPublicUrn(TestCase):
    def test_assign_public_urn_twice_doesnt_change_urn(self):
        exp = ExperimentSetFactory()
        publish_dataset(exp)
        exp.refresh_from_db()
        old_urn = exp.urn
        self.assertTrue(exp.has_public_urn)

        exp = ExperimentSet.objects.first()
        assign_public_urn(exp)
        exp.refresh_from_db()
        new_urn = exp.urn

        self.assertTrue(exp.has_public_urn)
        self.assertEqual(new_urn, old_urn)
