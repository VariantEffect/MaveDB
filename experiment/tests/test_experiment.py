
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
        self.expset_accession = "EXPS000001"
        self.exp_accession_1 = "EXP000001A"
        self.exp_accession_2 = "EXP000001B"
        self.target = "target"
        self.wt_seq = "ATCG"
        self.expset = ExperimentSet(accession=self.expset_accession)
        self.expset.save()

    def make_experiment(self, acc, save=True):
        exp = Experiment(
            accession=acc, experimentset=self.expset,
            target=self.target, wt_sequence=self.wt_seq)
        if save:
            exp.save()
        return exp

    def test_can_create_minimal_experiment(self):
        self.make_experiment(acc=self.exp_accession_1)
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.pk, 1)
        self.assertEqual(exp.accession, self.exp_accession_1)
        self.assertEqual(exp.experimentset, self.expset)

    def test_autoassign_accession_in_experimentset(self):
        self.make_experiment(acc=Experiment.build_accession(self.expset))
        self.make_experiment(acc=Experiment.build_accession(self.expset))

        exp1 = Experiment.objects.all()[0]
        exp2 = Experiment.objects.all()[1]
        self.assertEqual(exp1.accession, self.exp_accession_1)
        self.assertEqual(exp2.accession, self.exp_accession_2)

    def test_cannot_create_accessions_with_duplicate_accession(self):
        self.make_experiment(acc=self.exp_accession_1)
        with self.assertRaises(IntegrityError):
            self.make_experiment(acc=self.exp_accession_1)

    def test_cannot_create_experiment_null_experimentset(self):
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(
                accession=self.exp_accession_1,
                target=self.target,
                wt_sequence=self.wt_seq
            )

    def test_cannot_create_experiment_null_accession(self):
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(
                experimentset=self.expset,
                target=self.target,
                wt_sequence=self.wt_seq
            )

    def test_cannot_create_experiment_null_target(self):
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(
                accession=self.exp_accession_1,
                experimentset=self.expset,
                wt_sequence=self.wt_seq
            )

    def test_cannot_create_experiment_null_wt_seq(self):
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(
                accession=self.exp_accession_1,
                experimentset=self.expset,
                target=self.target
            )

    def test_experiments_sorted_by_most_recent(self):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() + datetime.timedelta(days=1)
        exp_1 = Experiment.objects.create(
            accession=self.exp_accession_1,
            experimentset=self.expset,
            target=self.target,
            wt_sequence=self.wt_seq,
            creation_date=date_1)
        exp_2 = Experiment.objects.create(
            accession=self.exp_accession_2,
            experimentset=self.expset,
            target=self.target,
            wt_sequence=self.wt_seq,
            creation_date=date_2)
        self.assertEqual(
            exp_2.accession, Experiment.objects.all()[0].accession)

    def test_new_experiment_has_todays_date_by_default(self):
        self.make_experiment(acc=self.exp_accession_1)
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.creation_date, datetime.date.today())

    def test_experiment_not_approved_by_default(self):
        self.make_experiment(acc=self.exp_accession_1)
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.approved, False)
