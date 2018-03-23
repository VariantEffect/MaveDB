
import datetime

from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TransactionTestCase

from dataset.models import Experiment, ExperimentSet


class TestExperimentSet(TransactionTestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ExperimentSet`, representing an experiment with associated
    :py:class:`Experiment` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """
    reset_sequences = True

    def setUp(self):
        self.expset_accession_1 = "EXPS000001"
        self.expset_accession_2 = "EXPS000002"
        self.expset_accession_3 = "EXPS000003"
        self.exp_accession_1 = "EXP000001A"
        self.exp_accession_2 = "EXP000001B"
        self.target = "target"
        self.wt_seq = "ATCG"

    def test_new_experiment_is_assigned_all_permission_groups(self):
        obj = ExperimentSet.objects.create()
        print(obj)
        self.assertEqual(Group.objects.count(), 3)

    def test_publish_updates_published_and_last_edit_dates(self):
        exps = ExperimentSet.objects.create()
        exps.publish()
        self.assertEqual(exps.publish_date, datetime.date.today())
        self.assertEqual(exps.last_edit_date, datetime.date.today())

    def test_publish_updates_private_to_false(self):
        exps = ExperimentSet.objects.create()
        exps.publish()
        self.assertFalse(exps.private)

    def test_can_create_minimal_experimentset(self):
        ExperimentSet.objects.create()
        expset = ExperimentSet.objects.all()[0]
        self.assertEqual(expset.pk, 1)
        self.assertEqual(expset.accession, self.expset_accession_1)
        self.assertEqual(expset.experiment_set.count(), 0)

    def test_autoassign_accession_in_experimentset(self):
        expset1 = ExperimentSet.objects.create()
        expset2 = ExperimentSet.objects.create()
        expset3 = ExperimentSet.objects.create()

        self.assertEqual(expset1.accession, self.expset_accession_1)
        self.assertEqual(expset2.accession, self.expset_accession_2)
        self.assertEqual(expset3.accession, self.expset_accession_3)

    def test_autoassign_does_not_reassign_deleted_accession(self):
        expset1 = ExperimentSet.objects.create()
        expset2 = ExperimentSet.objects.create()
        self.assertEqual(expset1.accession, self.expset_accession_1)
        self.assertEqual(expset2.accession, self.expset_accession_2)

        expset2.delete()
        expset3 = ExperimentSet.objects.create()
        self.assertEqual(expset3.accession, self.expset_accession_3)

    def test_cannot_create_experimentsets_with_duplicate_accession(self):
        ExperimentSet(accession=self.expset_accession_1).save()
        with self.assertRaises(IntegrityError):
            ExperimentSet(accession=self.expset_accession_1).save()

    def test_experimentsets_sorted_by_most_recent(self):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() + datetime.timedelta(days=1)
        exp_1 = ExperimentSet.objects.create(creation_date=date_1)
        exp_2 = ExperimentSet.objects.create(creation_date=date_2)
        self.assertEqual(exp_2, ExperimentSet.objects.all()[0])

    def test_new_experimentset_has_todays_date_by_default(self):
        ExperimentSet.objects.create()
        expset = ExperimentSet.objects.all()[0]
        self.assertEqual(expset.creation_date, datetime.date.today())

    def test_experimentset_not_approved_and_private_by_default(self):
        ExperimentSet.objects.create()
        expset = ExperimentSet.objects.all()[0]
        self.assertFalse(expset.approved)
        self.assertTrue(expset.private)

    def test_cannot_delete_experimentset_with_experiments(self):
        expset = ExperimentSet.objects.create()
        exp = self.make_experiment(expset=expset)
        with self.assertRaises(ProtectedError):
            expset.delete()

    def test_can_assign_next_experiment_suffix(self):
        expset = ExperimentSet.objects.create()
        self.assertEqual(expset.next_experiment_suffix(), 'A')
        expset.last_used_suffix = 'A'
        expset.save()
        self.assertEqual(expset.next_experiment_suffix(), 'B')

    def test_experiment_suffix_wraps_by_increasing_letter_count(self):
        expset = ExperimentSet.objects.create(last_used_suffix='Z')
        self.assertEqual(expset.next_experiment_suffix(), 'AA')

    def test_delete_does_not_rollback_experiment_suffix(self):
        expset = ExperimentSet.objects.create()

        exp = self.make_experiment(expset=expset)
        self.assertEqual(expset.last_used_suffix, 'A')

        exp.delete()
        self.assertEqual(expset.last_used_suffix, 'A')

        exp = self.make_experiment(expset=expset)
        self.assertEqual(expset.last_used_suffix, 'B')
