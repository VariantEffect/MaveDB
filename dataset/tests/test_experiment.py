import datetime

from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from genome.factories import TargetOrganismFactory

from ..factories import ExperimentFactory, ScoreSetFactory
from ..models.experimentset import ExperimentSet

class TestExperiment(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`Experiment`, representing an experi ment with associated
    :py:class:`ScoreSet` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    def test_publish_updates_published_and_last_edit_dates(self):
        exp = ExperimentFactory()
        exp.publish()
        self.assertEqual(exp.publish_date, datetime.date.today())
        self.assertEqual(exp.last_edit_date, datetime.date.today())

    def test_publish_updates_private_to_false(self):
        exp = ExperimentFactory()
        exp.publish()
        self.assertFalse(exp.private)

    def test_new_experiment_is_assigned_all_permission_groups(self):
        self.assertEqual(Group.objects.count(), 0)
        _ = ExperimentFactory()
        self.assertEqual(Group.objects.count(), 6)

    def test_deleted_experiment_deletes_all_permission_groups(self):
        obj = ExperimentFactory()
        self.assertEqual(Group.objects.count(), 6)
        obj.delete()
        self.assertEqual(Group.objects.count(), 3)

    def test_autoassign_does_not_reassign_deleted_urn(self):
        exps1 = ExperimentFactory()
        previous = exps1.urn
        exps1.delete()
        exps2 = ExperimentFactory()
        self.assertGreater(exps2.urn, previous)

    def test_cannot_create_with_duplicate_urn(self):
        obj = ExperimentFactory()
        with self.assertRaises(IntegrityError):
            ExperimentFactory(urn=obj.urn)

    def test_cannot_create_experiment_null_target(self):
        with self.assertRaises(IntegrityError):
            ExperimentFactory(target=None)

    def test_cannot_create_experiment_null_wt_seq(self):
        with self.assertRaises(AttributeError):
            ExperimentFactory(wt_sequence=None)

    def test_experiment_not_approved_and_private_by_default(self):
        exp = ExperimentFactory()
        self.assertFalse(exp.approved)
        self.assertTrue(exp.private)

    def test_cannot_delete_experiment_with_scoresets(self):
        scs = ScoreSetFactory()
        with self.assertRaises(ProtectedError):
            scs.experiment.delete()

    def test_update_target_organism(self):
        exp = ExperimentFactory()
        new = TargetOrganismFactory()
        exp.update_target_organism(new)
        exp.save()
        exp.refresh_from_db()
        self.assertEqual(exp.get_target_organism_name(), new.text)
        self.assertEqual(exp.target_organism.count(), 1)

    def test_typeerror_target_organism_not_target_organism_instance(self):
        exp = ExperimentFactory()
        with self.assertRaises(TypeError):
            exp.update_target_organism('Mouse')

    def test_creates_experimentset_if_none_when_saved(self):
        exp = ExperimentFactory(experimentset=None)  # invokes save
        self.assertEqual(exp.experimentset, ExperimentSet.objects.first())
