

from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase

from experiment.models import Experiment
from scoreset.models import ScoreSet, Variant
from scoreset.forms import ScoreSetForm
from scoreset.validators import Constants


class TestScoreSetForm(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.experiment = Experiment.objects.create(
            target="test", wt_sequence="ATCG"
        )

    def make_test_data(self, use_exp=True):
        data = {
            Constants.SCORES_DATA: "hgvs,score,se\nc.54A>G,0.5,0.4\n",
            Constants.COUNTS_DATA: "hgvs,count\nc.54A>G,10\n",
            "experiment": self.experiment.pk if use_exp else None,
            "metadata": {"fastq_min_count": "4"}
        }
        return data

    def test_can_create_from_form(self):
        form = ScoreSetForm(data=self.make_test_data())
        form.is_valid()
        model = form.save()
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.all()[0].pk, 1)
        self.assertEqual(Variant.objects.all()[0].pk, 1)

    def test_not_valid_experiment_not_found(self):
        data = self.make_test_data()
        data["experiment"] = 100
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_can_create_from_instance(self):
        scs = ScoreSet.objects.create(experiment=self.experiment)
        form = ScoreSetForm(
            data=self.make_test_data(),
            instance=scs
        )
        model = form.save()
        self.assertEqual(Experiment.objects.count(), 1)
        self.assertEqual(model.variant_set.count(), 1)

    def test_invalid_incorrect_scores_header(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = "bbbb,score,se\nc.54A>G,0.5,0.4"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_can_save_multiple_variants(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] += "c.18A>T,0.6,0.1"
        data[Constants.COUNTS_DATA] += "c.18A>T,4"
        form = ScoreSetForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Variant.objects.count(), 2)

    def test_nans_are_valid(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = \
            "hgvs,col1,col2,col3,col4\nc.18A>T,nan,na,none,"
        data[Constants.COUNTS_DATA] = "hgvs,count\nc.18A>T,1"
        form = ScoreSetForm(data=data)
        form.save()
        var = Variant.objects.all()[0]
        self.assertEqual(var.data['counts']['count'], 1)
        self.assertEqual(var.data['scores']['col1'], None)
        self.assertEqual(var.data['scores']['col2'], None)
        self.assertEqual(var.data['scores']['col3'], None)
        self.assertEqual(var.data['scores']['col4'], None)

    def test_invalid_variant_score_row_missing_data(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = "hgvs,score,se\n0.5,0.4"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_score_row_extra_data(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = "hgvs,score,se\ntest,0.5,0.4,extra"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_score_row_non_numeric_data(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = "hgvs,score,se\ntest,h,f,f"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_count_row_non_numeric_data(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = "hgvs,count\nhello"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_count_row_missing_data(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\n1"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_count_row_extra_data(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\ntest,1,1"
        form = ScoreSetForm(data=data)
        self.assertFalse(form.is_valid())

    def test_blank_values_still_valid(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\ntest,"
        data[Constants.SCORES_DATA] = "hgvs,score,se\ntest,,"
        form = ScoreSetForm(data=data)
        self.assertTrue(form.is_valid())

    def test_blank_values_convert_to_none(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\ntest,"
        data[Constants.SCORES_DATA] = "hgvs,score,se\ntest,1,"
        form = ScoreSetForm(data=data)
        form.save()
        var = Variant.objects.all()[0]
        self.assertEqual(var.data['counts']['count'], None)
        self.assertEqual(var.data['scores']['score'], 1.0)
        self.assertEqual(var.data['scores']['se'], None)

    def test_can_defer_save(self):
        form = ScoreSetForm(data=self.make_test_data())
        model = form.save(commit=False)
        model.save()
        form.save_variants()
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.all()[0].pk, 1)
        self.assertEqual(Variant.objects.all()[0].pk, 1)

    def test_invalid_hgvs_strings_do_not_match_in_scores_and_counts_data(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\ntest,1"
        data[Constants.SCORES_DATA] = "hgvs,score,se\nTEST,1,1"
        form = ScoreSetForm(data=data)
        form_is_valid = form.is_valid()
        self.assertFalse(form_is_valid)

    def test_invalid_scores_counts_data_non_matching_length(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\ninvalid,1\ntest,1"
        data[Constants.SCORES_DATA] = "hgvs,score,se\nTEST,1,1"
        form = ScoreSetForm(data=data)
        form_is_valid = form.is_valid()
        self.assertFalse(form_is_valid)

    def test_clean_filters_out_variants_with_nan_numeric_fields(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "hgvs,count\ntest,"
        data[Constants.SCORES_DATA] = "hgvs,score,se\ntest,,"
        form = ScoreSetForm(data=data)
        form.save()
        self.assertEqual(Variant.objects.count(), 0)

    def test_invalid_hgvs_not_first_column_in_count_data(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "count,hgvs\n1,test"
        form = ScoreSetForm(data=data)
        form_is_valid = form.is_valid()
        self.assertFalse(form_is_valid)

    def test_invalid_count_not_second_column_in_count_data(self):
        data = self.make_test_data()
        data[Constants.COUNTS_DATA] = "col1,col2,hgvs,count\n1,1,test,1"
        form = ScoreSetForm(data=data)
        form_is_valid = form.is_valid()
        self.assertFalse(form_is_valid)

    def test_invalid_hgvs_not_first_column_in_score_data(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] = "score,hgvs,se\n1,test,1"
        form = ScoreSetForm(data=data)
        form_is_valid = form.is_valid()
        self.assertFalse(form_is_valid)

    def test_trailing_whitespace_not_interpreted_as_variant(self):
        data = self.make_test_data()
        data[Constants.SCORES_DATA] += "\n\n\n\n"
        form = ScoreSetForm(data=data)
        form.save()
        self.assertEqual(Variant.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.count(), 1)

    def test_error_invalid_hgvs_string(self):
        self.fail("Write this test!")
