import datetime

from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import TransactionTestCase
from django.db.models import ProtectedError

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet, Variant
from scoreset.models import SCORES_KEY, COUNTS_KEY


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

    def test_validation_error_json_no_scores_key(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={"not scores": [], COUNTS_KEY: []}
        )
        with self.assertRaises(ValidationError):
            scs.full_clean()

    def test_validation_error_json_no_counts_key(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={SCORES_KEY: [], "not counts": []}
        )
        with self.assertRaises(ValidationError):
            scs.full_clean()

    def test_validation_error_json_unexpected_keys(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={
                SCORES_KEY: [], COUNTS_KEY: [], "extra": [], "jumbo": []
            }
        )
        with self.assertRaises(ValidationError):
            scs.full_clean()

    def test_validation_error_json_value_not_list(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={SCORES_KEY: 1, COUNTS_KEY: 2}
        )
        with self.assertRaises(ValidationError):
            scs.full_clean()

    def test_validation_error_json_list_not_strings(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={SCORES_KEY: [1], COUNTS_KEY: [1]}
        )
        with self.assertRaises(ValidationError):
            scs.full_clean()

    def test_validation_error_json_list_empty(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={SCORES_KEY: [], COUNTS_KEY: [1]}
        )
        with self.assertRaises(ValidationError):
            scs.full_clean()

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

    def test_scoreset_cannot_validate_negative_last_used_suffix(self):
        with self.assertRaises(ValidationError):
            ScoreSet.objects.create(
                experiment=self.exp,
                last_used_suffix=-1
            ).full_clean()

    def test_cannot_delete_scoreset_with_variants(self):
        scs = ScoreSet.objects.create(experiment=self.exp)
        var = Variant.objects.create(
            scoreset=scs,
            hgvs="hgvs",
        )
        with self.assertRaises(ProtectedError):
            scs.delete()

    def test_delete_does_not_rollback_variant_accession(self):
        scs = ScoreSet.objects.create(experiment=self.exp)
        Variant.objects.create(scoreset=scs, hgvs="hgvs")
        var = Variant.objects.create(scoreset=scs, hgvs="hgvs")
        var.delete()
        var = Variant.objects.create(scoreset=scs, hgvs="hgvs")
        self.assertEqual(var.accession[-1], '3')

    def test_can_associate_valid_variant(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={SCORES_KEY: ['score'], COUNTS_KEY: ['count']}
        )
        var = Variant.objects.create(
            scoreset=scs, hgvs="hgvs",
            data={SCORES_KEY: {'score': 1}, COUNTS_KEY: {'count': 1}}
        )
        scs.validate_variant_data(var)  # should pass

    def test_cannot_associate_variant_with_nonmatching_data_columns(self):
        scs = ScoreSet.objects.create(
            experiment=self.exp,
            dataset_columns={SCORES_KEY: ['score'], COUNTS_KEY: ['count']}
        )
        var = Variant.objects.create(
            scoreset=scs, hgvs="hgvs",
            data={
                SCORES_KEY: {'score': 1, 'SE': 1},
                COUNTS_KEY: {'count': 1}
            }
        )
        with self.assertRaises(ValueError):
            scs.validate_variant_data(var)


class TestVariant(TransactionTestCase):
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
        self.scs_1 = ScoreSet.objects.create(experiment=self.exp)
        self.scs_2 = ScoreSet.objects.create(experiment=self.exp)

        self.hgvs_1 = "c.45C>G"
        self.hgvs_2 = "c.1A>T"
        self.var_accession_11 = "SCSVAR000001A.1.1"
        self.var_accession_12 = "SCSVAR000001A.1.2"
        self.var_accession_21 = "SCSVAR000001A.2.1"
        self.var_accession_22 = "SCSVAR000001A.2.2"

    def test_can_create_minimal_variant(self):
        Variant.objects.create(scoreset=self.scs_1, hgvs=self.hgvs_1)
        var = Variant.objects.all()[0]
        self.assertEqual(var.accession, self.var_accession_11)
        self.assertEqual(var.scoreset, self.scs_1)

    def test_autoassign_accession_in_variant(self):
        Variant.objects.create(scoreset=self.scs_1, hgvs=self.hgvs_1)
        Variant.objects.create(scoreset=self.scs_1, hgvs=self.hgvs_2)

        var_1 = Variant.objects.all()[0]
        var_2 = Variant.objects.all()[1]
        self.assertEqual(var_1.accession, self.var_accession_11)
        self.assertEqual(var_2.accession, self.var_accession_12)

    def test_cannot_create_variant_with_duplicate_accession(self):
        Variant.objects.create(
            scoreset=self.scs_1,
            hgvs=self.hgvs_1
        )
        with self.assertRaises(IntegrityError):
            Variant.objects.create(
                accession=self.var_accession_11,
                hgvs=self.hgvs_1,
                scoreset=self.scs_1
            )

    def test_cannot_save_without_scoreset(self):
        with self.assertRaises(IntegrityError):
            Variant.objects.create(
                accession=self.var_accession_11,
                hgvs=self.hgvs_1
            )
        with self.assertRaises(IntegrityError):
            Variant.objects.create(hgvs=self.hgvs_1)

    def test_cannot_save_without_hgvs(self):
        with self.assertRaises(IntegrityError):
            Variant.objects.create(
                scoreset=self.scs_1
            )

    def test_validation_error_json_no_scores_key(self):
        var = Variant.objects.create(
            scoreset=self.scs_1,
            hgvs=self.hgvs_1,
            data={"not scores": {}, COUNTS_KEY: {}}
        )
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_validation_error_json_no_counts_key(self):
        var = Variant.objects.create(
            scoreset=self.scs_1,
            hgvs=self.hgvs_1,
            data={SCORES_KEY: {}, "not counts": {}}
        )
        with self.assertRaises(ValidationError):
            var.full_clean()

    def test_variants_sorted_by_most_recent(self):
        date_1 = datetime.date.today()
        date_2 = datetime.date.today() + datetime.timedelta(days=1)
        Variant.objects.create(
            scoreset=self.scs_1,
            hgvs=self.hgvs_1,
            creation_date=date_1
        )
        Variant.objects.create(
            scoreset=self.scs_1,
            hgvs=self.hgvs_1,
            creation_date=date_2
        )
        self.assertEqual(
            self.var_accession_12, Variant.objects.all()[0].accession)

    def test_new_variant_has_todays_date_by_default(self):
        Variant.objects.create(
            scoreset=self.scs_1,
            hgvs=self.hgvs_1,
        )
        var = Variant.objects.all()[0]
        self.assertEqual(var.creation_date, datetime.date.today())
