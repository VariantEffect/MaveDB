
import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TransactionTestCase


from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet


class TestExperiment(TransactionTestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`Experiment`, representing an experiment with associated
    :py:class:`ScoreSet` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    reset_sequences = True

    def setUp(self):
        self.expset_accession = "EXPS000001"
        self.exp_accession_1 = "EXP000001A"
        self.exp_accession_2 = "EXP000001B"
        self.target = "target"
        self.wt_seq = "ATCG"

    def make_experiment(self, acc=None, expset=None, save=True):
        exp = Experiment(
            accession=acc,
            experimentset=expset,
            target=self.target,
            wt_sequence=self.wt_seq
        )
        if save:
            exp.save()
        return exp

    def test_can_create_minimal_experiment(self):
        Experiment.objects.create(
            target=self.target,
            wt_sequence=self.wt_seq
        )
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.accession, self.exp_accession_1)
        self.assertEqual(exp.experimentset.accession, self.expset_accession)

    def test_autoassign_accession_in_experimentset(self):
        expset = ExperimentSet.objects.create()

        self.make_experiment(expset=expset)
        self.make_experiment(expset=expset)

        exp1 = Experiment.objects.all()[0]
        exp2 = Experiment.objects.all()[1]
        self.assertEqual(exp1.accession, self.exp_accession_1)
        self.assertEqual(exp2.accession, self.exp_accession_2)

    def test_cannot_create_accessions_with_duplicate_accession(self):
        self.make_experiment(acc=self.exp_accession_1)
        with self.assertRaises(IntegrityError):
            self.make_experiment(acc=self.exp_accession_1)

    def test_cannot_create_experiment_null_target(self):
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(
                accession=self.exp_accession_1,
                experimentset=ExperimentSet.objects.create(),
                wt_sequence=self.wt_seq
            )

    def test_cannot_create_experiment_null_wt_seq(self):
        with self.assertRaises(IntegrityError):
            Experiment.objects.create(
                accession=self.exp_accession_1,
                experimentset=ExperimentSet.objects.create(),
                target=self.target
            )

    def test_experiments_sorted_by_most_recent(self):
        expset = ExperimentSet.objects.create()
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() + datetime.timedelta(days=1)
        exp_1 = Experiment.objects.create(
            accession=self.exp_accession_1,
            experimentset=expset,
            target=self.target,
            wt_sequence=self.wt_seq,
            creation_date=date_1)
        exp_2 = Experiment.objects.create(
            accession=self.exp_accession_2,
            experimentset=expset,
            target=self.target,
            wt_sequence=self.wt_seq,
            creation_date=date_2)
        self.assertEqual(
            exp_2.accession, Experiment.objects.all()[0].accession)

    def test_new_experiment_has_todays_date_by_default(self):
        self.make_experiment(acc=self.exp_accession_1)
        exp = Experiment.objects.all()[0]
        self.assertEqual(exp.creation_date, datetime.date.today())

    def test_experiment_not_approved_and_private_by_default(self):
        self.make_experiment(acc=self.exp_accession_1)
        exp = Experiment.objects.all()[0]
        self.assertFalse(exp.approved)
        self.assertTrue(exp.private)

    def test_cannot_delete_experiment_with_scoresets(self):
        exp = self.make_experiment()
        scs = ScoreSet.objects.create(experiment=exp)
        with self.assertRaises(ProtectedError):
            exp.delete()

    def test_can_autoassign_scoreset_accession(self):
        exp = self.make_experiment()
        scs = ScoreSet.objects.create(experiment=exp)
        expected = exp.accession.replace(
            exp.ACCESSION_PREFIX, scs.ACCESSION_PREFIX
        ) + ".1"
        self.assertEqual(scs.accession, expected)

    def test_delete_does_not_rollback_scoreset_accession(self):
        exp = self.make_experiment()
        scs = ScoreSet.objects.create(experiment=exp)
        scs.delete()
        scs = ScoreSet.objects.create(experiment=exp)
        expected = exp.accession.replace(
            exp.ACCESSION_PREFIX, scs.ACCESSION_PREFIX
        ) + ".2"
        self.assertEqual(scs.accession, expected)
