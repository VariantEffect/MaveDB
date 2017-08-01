
import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from experiment.models import Experiment, ExperimentSet


class TestExperiment(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`Experiment`, representing an experiment with associated
    :py:class:`ScoreSet` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_can_experiment_uses_accession_as_pk(self):
        Experiment(accession="EXP000001").save()
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.pk, "EXP000001")

    def test_can_create_experiment_with_create(self):
        Experiment(accession="EXP000001").save()
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.accession, "EXP000001")

    def test_can_create_experiment_with_manager(self):
        exp = Experiment.objects.create(accession="EXP000001")
        self.assertEqual(exp.accession, "EXP000001")

    def test_accession_increment_correctly(self):
        Experiment.objects.create(accession=Experiment.next_accession())
        Experiment.objects.create(accession=Experiment.next_accession())

        exp1, exp2 = Experiment.objects.all()
        self.assertEqual(exp1.accession, "EXP000001")
        self.assertEqual(exp2.accession, "EXP000002")

    def test_cannot_create_accessions_with_duplicate_accession(self):
        Experiment.objects.create(accession="EXP000001")
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(accession="EXP000001")

    def test_experiments_sorted_by_most_recent(self):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() + datetime.timedelta(days=1)
        exp_1 = Experiment.objects.create(
            accession=Experiment.next_accession(), creation_date=date_1)
        exp_2 = Experiment.objects.create(
            accession=Experiment.next_accession(), creation_date=date_2)

        self.assertEqual(
            exp_2.accession, Experiment.objects.all()[0].accession)

    def test_new_experiment_has_todays_date_by_default(self):
        Experiment().save()
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.creation_date, datetime.date.today())

    def test_experiment_not_approved_by_default(self):
        Experiment().save()
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.approved, False)

    def test_experiment_can_be_owned_by_multiple_users(self):
        UserModel = get_user_model()
        u1 = UserModel.objects.create(username="farva")
        u2 = UserModel.objects.create(username="bertha")

        exp = Experiment.objects.create()
        exp.owners = [u1, u2]
        exp.save()

        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.owners.all()[0], u1)
        self.assertEqual(exp.owners.all()[1], u2)

    def test_active_owners_properly_returned(self):
        UserModel = get_user_model()
        u1 = UserModel.objects.create(username="farva")
        u2 = UserModel.objects.create(username="bertha")

        exp = Experiment.objects.create()
        exp.owners = [u1, u2]
        exp.save()

        exp = Experiment.objects.all()[0]
        self.assertEqual(list(exp.active_owners), [u1, u2])

    def test_inactive_owners_properly_returned(self):
        UserModel = get_user_model()
        u1 = UserModel.objects.create(username="farva", is_active=False)
        u2 = UserModel.objects.create(username="bertha")

        exp = Experiment.objects.create()
        exp.owners = [u1, u2]
        exp.save()

        exp = Experiment.objects.all()[0]
        self.assertEqual(list(exp.inactive_owners), [u1])

    def test_all_owners_properly_returned(self):
        UserModel = get_user_model()
        u1 = UserModel.objects.create(username="farva", is_active=False)
        u2 = UserModel.objects.create(username="bertha")

        exp = Experiment.objects.create()
        exp.owners = [u1, u2]
        exp.save()

        exp = Experiment.objects.all()[0]
        self.assertEqual(list(exp.all_owners), [u1, u2])

    def test_deleted_owner_empty_owners_query_set(self):
        UserModel = get_user_model()
        u1 = UserModel.objects.create(username="farva")

        exp = Experiment.objects.create()
        exp.owners.add(u1)
        exp.save()

        self.assertEqual(exp.all_owners.count(), 1)

        u1.delete()
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.all_owners.count(), 0)

    def test_assign_to_default_experiment_set(self):
        exp = Experiment()
        self.assertEqual(exp.experiment_set, None)
        self.assertEqual(ExperimentSet.objects.count(), 0)

        exp.assign_to_default_experiment_set()
        self.assertEqual(ExperimentSet.objects.count(), 1)

        exp = Experiment.objects.all()[0]
        exp_set = ExperimentSet.objects.all()[0]
        self.assertEqual(exp.experiment_set, exp_set)

    def test_default_experiment_set_inherits_owners(self):
        UserModel = get_user_model()
        u1 = UserModel.objects.create(username="farva")

        exp = Experiment.objects.create()
        exp.owners.add(u1)
        exp.save()
        exp.assign_to_default_experiment_set()

        exp = Experiment.objects.all()[0]
        exp_set = ExperimentSet.objects.all()[0]
        print(exp_set)
        self.assertEqual(list(exp.all_owners), list(exp_set.all_owners))
