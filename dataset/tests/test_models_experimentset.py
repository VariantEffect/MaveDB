from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.shortcuts import reverse

from core.utilities import base_url

from urn.validators import MAVEDB_EXPERIMENTSET_URN_RE

from ..models.base import PublicDatasetCounter
from ..models.experimentset import ExperimentSet, assign_public_urn
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
    def setUp(self):
        self.factory = ExperimentSetFactory
        self.counter = PublicDatasetCounter.load()
    
    def test_assigns_public_urn(self):
        instance = self.factory()
        instance = assign_public_urn(instance)
        self.assertIsNotNone(
            MAVEDB_EXPERIMENTSET_URN_RE.fullmatch(instance.urn))
        self.assertTrue(instance.has_public_urn)
    
    def test_increments_parent_last_child_value(self):
        instance = self.factory()
        self.assertEqual(self.counter.experimentsets, 0)
        assign_public_urn(instance)
        self.counter.refresh_from_db()
        self.assertEqual(self.counter.experimentsets, 1)
       
    def test_assigns_sequential_urns(self):
        instance1 = self.factory()
        instance2 = self.factory()
        instance1 = assign_public_urn(instance1)
        instance2 = assign_public_urn(instance2)
        self.assertEqual(instance1.urn[-1], '1')
        self.assertEqual(instance2.urn[-1], '2')
    
    def test_applying_twice_does_not_change_urn(self):
        instance = self.factory()
        i1 = assign_public_urn(instance)
        i2 = assign_public_urn(instance)
        self.assertEqual(i1.urn, i2.urn)
