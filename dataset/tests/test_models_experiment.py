import datetime

from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from ..factories import ExperimentFactory, ScoreSetFactory, ScoreSetWithTargetFactory
from ..models.experimentset import ExperimentSet
from ..models.experiment import Experiment


class TestExperiment(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`Experiment`, representing an experi ment with associated
    :py:class:`ScoreSet` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    def test_publish_updates_published_and_modification_dates(self):
        exp = ExperimentFactory()
        exp.publish()
        self.assertEqual(exp.publish_date, datetime.date.today())
        self.assertEqual(exp.modification_date, datetime.date.today())

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
        exps1 = ExperimentFactory(
            private=False,
            experimentset__private=False
        )
        previous = exps1.urn
        exps1.delete()
        exps2 = ExperimentFactory(
            private=False,
            experimentset__private=False
        )
        self.assertGreater(exps2.urn, previous)

    def test_cannot_create_with_duplicate_urn(self):
        obj = ExperimentFactory()
        with self.assertRaises(IntegrityError):
            ExperimentFactory(urn=obj.urn)

    def test_experiment_not_approved_and_private_by_default(self):
        exp = Experiment()
        self.assertFalse(exp.approved)
        self.assertTrue(exp.private)

    def test_cannot_delete_experiment_with_scoresets(self):
        scs = ScoreSetFactory()
        with self.assertRaises(ProtectedError):
            scs.experiment.delete()

    def test_creates_experimentset_if_none_when_saved(self):
        exp = ExperimentFactory(experimentset=None)  # invokes save
        self.assertEqual(exp.experimentset, ExperimentSet.objects.first())

    def test_get_targets_returns_empty_qs(self):
        exp = ExperimentFactory(experimentset=None)
        self.assertEqual(exp.get_targets().count(), 0)

    def test_get_target_organisms_returns_sorted(self):
        exp = ExperimentFactory(experimentset=None)

        scs1 = ScoreSetWithTargetFactory(experiment=exp)
        scs2 = ScoreSetWithTargetFactory(experiment=exp)
        genome1 = scs1.target.get_reference_genomes().first()
        genome2 = scs2.target.get_reference_genomes().first()

        genome1.species_name = 'A'
        genome1.save()
        genome2.species_name = 'B'
        genome2.save()

        expected = sorted(set(
            [genome1.format_species_name_html()] +
            [genome2.format_species_name_html()]
        ))
        self.assertEqual(exp.get_targets().count(), 2)
        self.assertEqual(exp.get_display_target_organisms(), expected)

        expected = sorted(set(
            [genome1.get_species_name()] +
            [genome2.get_species_name()]
        ))
        self.assertEqual(exp.get_target_organisms(), expected)

    def test_publish_twice_doesnt_change_urn(self):
        exp = ExperimentFactory()
        exp.publish()
        exp.refresh_from_db()
        old_urn = exp.urn
        self.assertTrue(exp.has_public_urn)

        exp = Experiment.objects.first()
        exp.publish()
        exp.refresh_from_db()
        new_urn = exp.urn

        self.assertTrue(exp.has_public_urn)
        self.assertEqual(new_urn, old_urn)
