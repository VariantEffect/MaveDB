import datetime

from django.db import IntegrityError
from django.test import TransactionTestCase

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet


class TestScoreSet(TransactionTestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ScoreSet`, representing an experiment with associated
    :py:class:`Variant` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    reset_sequences = True

    def setUp(self):
        self.target = "target"
        self.wt_seq = "ATCG"
        self.exp = Experiment.objects.create(
            target=self.target,
            wt_sequence=self.wt_seq
        )
        self.exp_accession = "EXP000001A"
        self.scs_accession_1 = "SCS000001A.1"
        self.scs_accession_2 = "SCS000001A.2"

    def test_can_create_minimal_scoreset(self):
        scs = ScoreSet.objects.create(experiment=self.exp)
        self.assertEqual(scs.accession, self.scs_accession_1)
        self.assertEqual(scs.experiment.accession, self.exp_accession)

    def test_autoassign_accession_in_scoreset(self):
        ScoreSet.objects.create(experiment=self.exp)
        ScoreSet.objects.create(experiment=self.exp)

        scs_1 = ScoreSet.objects.all()[0]
        scs_2 = ScoreSet.objects.all()[1]
        self.assertEqual(scs_1.accession, self.scs_accession_1)
        self.assertEqual(scs_2.accession, self.scs_accession_2)

    def test_cannot_create_scoreset_with_duplicate_accession(self):
        ScoreSet.objects.create(experiment=self.exp)
        with self.assertRaises(IntegrityError):
            ScoreSet.objects.create(
                accession=self.scs_accession_1,
                experiment=self.exp
            )

    def test_cannot_save_without_experiment(self):
        with self.assertRaises(IntegrityError):
            ScoreSet.objects.create(accession=self.scs_accession_1)
        with self.assertRaises(IntegrityError):
            ScoreSet.objects.create()

    def test_validation_error_wront_format_json_field(self):
        self.fail("Write this test!")

    def test_scoresets_sorted_by_most_recent(self):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() + datetime.timedelta(days=1)
        scs_1 = ScoreSet.objects.create(
            experiment=self.exp,
            creation_date=date_1)
        scs_2 = ScoreSet.objects.create(
            experiment=self.exp,
            creation_date=date_2)
        self.assertEqual(
            self.scs_accession_2, ScoreSet.objects.all()[0].accession)

    def test_new_scoreset_has_todays_date_by_default(self):
        ScoreSet.objects.create(experiment=self.exp)
        scs = ScoreSet.objects.all()[0]
        self.assertEqual(scs.creation_date, datetime.date.today())

    def test_scoreset_not_approved_and_private_by_default(self):
        ScoreSet.objects.create(experiment=self.exp)
        scs = ScoreSet.objects.all()[0]
        self.assertFalse(scs.approved)
        self.assertTrue(scs.private)

    def test_cannot_delete_scoreset_with_variants(self):
        self.fail("Write this test!")

    def test_can_autoassign_variant_accession(self):
        self.fail("Write this test!")

    def test_delete_does_not_rollback_variant_accession(self):
        self.fail("Write this test!")

    def test_can_associate_valid_variant(self):
        self.fail("Write this test!")

    def test_cannot_associate_variant_with_nonmatching_data_columns(self):
        self.fail("Write this test!")


class TestVariant(TransactionTestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ScoreSet`, representing an experiment with associated
    :py:class:`Variant` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """

    reset_sequences = True

    def setUp(self):
        self.expset = ExperimentSet.objects.create(
            accession=ExperimentSet.build_accession())
        self.target = "target"
        self.wt_seq = "ATCG"
        self.exp = Experiment.objects.create(
            accession=Experiment.build_accession(self.expset),
            experimentset=self.expset,
            target=self.target, wt_sequence=self.wt_seq)

        self.scs_1 = ScoreSet.objects.create(
            accession=ScoreSet.build_accession(self.exp), experiment=exp)
        self.scs_2 = ScoreSet.objects.create(
            accession=ScoreSet.build_accession(self.exp), experiment=exp)
