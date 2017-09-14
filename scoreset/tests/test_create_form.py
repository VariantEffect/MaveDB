
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

from experiment.models import Experiment
from scoreset.models import ScoreSet, Variant
from scoreset.forms import ScoreSetForm
from scoreset.validators import Constants

from .utility import make_score_count_files

User = get_user_model()


class TestScoreSetForm(TestCase):

    def setUp(self):
        self.experiment = Experiment.objects.create(
            target="test", wt_sequence="ATCG"
        )

    def make_test_data(self, scores_data=None, counts_data=None, use_exp=True):
        data = {"experiment": self.experiment.pk if use_exp else None}
        s_file, c_file = make_score_count_files(scores_data, counts_data)
        files = {Constants.SCORES_DATA: s_file}
        if c_file is not None:
            files[Constants.COUNTS_DATA] = c_file
        return data, files

    def test_can_create_from_form(self):
        data, files = self.make_test_data()
        form = ScoreSetForm(data=data, files=files)
        form.is_valid()
        model = form.save()
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)

    def test_not_valid_experiment_not_found(self):
        data, files = self.make_test_data()
        data["experiment"] = 100
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_can_create_from_instance(self):
        data, files = self.make_test_data()
        scs = ScoreSet.objects.create(experiment=self.experiment)
        form = ScoreSetForm(
            data=data, files=files,
            instance=scs
        )
        model = form.save()
        self.assertEqual(Experiment.objects.count(), 1)
        self.assertEqual(model.variant_set.count(), 1)

    def test_invalid_incorrect_scores_header(self):
        data, files = self.make_test_data(
            scores_data="bbbb,score,se\nc.54A>G,0.5,0.4"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_can_save_multiple_variants(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,0.5,0.4\nc.18A>T,0.6,0.1\n",
            counts_data="hgvs,count\nc.54A>G,10\nc.18A>T,4\n"

        )
        form = ScoreSetForm(data=data, files=files)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Variant.objects.count(), 2)

    def test_nans_are_valid(self):
        data, files = self.make_test_data(
            scores_data=(
                "hgvs,col1,col2,col3,col4,col5\nc.54A>G,nan,na,none,1,\n"
            )
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        var = Variant.objects.all()[0]
        self.assertEqual(var.data['scores']['col1'], None)
        self.assertEqual(var.data['scores']['col2'], None)
        self.assertEqual(var.data['scores']['col3'], None)
        self.assertEqual(var.data['scores']['col4'], 1)
        self.assertEqual(var.data['scores']['col5'], None)

    def test_invalid_variant_score_row_missing_data(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,0.4"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_score_row_extra_data(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,0.5,0.4,extra"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_score_row_non_numeric_data(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,h,f,f"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_count_row_non_numeric_data(self):
        data, files = self.make_test_data(
            counts_data="hgvs,count\nc.54A>G,hello"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_count_row_missing_data(self):
        data, files = self.make_test_data(
            counts_data="hgvs,count,se\nc.54A>G,1"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_variant_count_row_extra_data(self):
        data, files = self.make_test_data(
            counts_data="hgvs,count\nc.54A>G,1,1"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_blank_values_still_valid(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,,1"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertTrue(form.is_valid())

    def test_blank_values_convert_to_none(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,,1"
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        var = Variant.objects.all()[0]
        self.assertEqual(var.data['scores']['score'], None)
        self.assertEqual(var.data['scores']['se'], 1.0)

    def test_can_defer_save(self):
        data, files = self.make_test_data()
        form = ScoreSetForm(data=data, files=files)
        model = form.save(commit=False)
        model.save()
        form.save_variants_and_set_dataset_columns()
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)

    def test_clean_filters_out_variants_with_nan_numeric_fields(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,,\nc.55A>G,1,1"
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        self.assertEqual(Variant.objects.count(), 1)

    def test_invalid_variant_appears_more_than_once(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,1,2\nc.54A>G,1,1"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_hgvs_not_first_column_in_count_data(self):
        data, files = self.make_test_data(
            counts_data="count,hgvs\n1,c.54A>G"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_invalid_hgvs_not_first_column_in_score_data(self):
        data, files = self.make_test_data(
            scores_data="score,hgvs\n1,c.54A>G"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_trailing_whitespace_not_interpreted_as_variant(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nc.54A>G,1,2\n\n\n\n"
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        self.assertEqual(Variant.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.count(), 1)

    def test_blank_lines_ignored(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\n\nc.54A>G,1,2"
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        self.assertEqual(Variant.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.count(), 1)

    def test_error_invalid_hgvs_string(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\nstring,1,2"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_error_invalid_mixed_hgvs_string(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score,se\n'n.54A>G, p.Ala101Gln',1,2"
        )
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_error_replaces_does_not_match_experiment_selection(self):
        data, files = self.make_test_data()
        new_exp = Experiment.objects.create(target="test", wt_sequence="atcg")
        new_scs = ScoreSet.objects.create(experiment=new_exp)
        data["replaces"] = new_scs.pk
        form = ScoreSetForm(data=data, files=files)
        self.assertFalse(form.is_valid())

    def test_variant_in_score_not_in_count_data_has_missing_data_filled(self):
        data, files = self.make_test_data(
            counts_data="hgvs,count\nc.55A>G,1"
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        var = Variant.objects.get(hgvs="c.54A>G")
        self.assertEqual(var.data["counts"]["count"], None)

    def test_variant_in_count_not_in_score_data_has_missing_data_filled(self):
        data, files = self.make_test_data(
            counts_data="hgvs,count\nc.55A>G,1"
        )
        form = ScoreSetForm(data=data, files=files)
        form.save()
        var = Variant.objects.get(hgvs="c.55A>G")
        self.assertEqual(var.data["scores"]["score"], None)
        self.assertEqual(var.data["scores"]["se"], None)

    def test_no_count_data_dataset_columns_at_counts_key_is_empty_list(self):
        data, files = self.make_test_data()
        form = ScoreSetForm(data=data, files=files)
        scs = form.save()
        self.assertEqual(scs.dataset_columns["counts"], [])

    def test_no_count_data_var_data_at_counts_is_empty_dict(self):
        data, files = self.make_test_data()
        form = ScoreSetForm(data=data, files=files)
        form.save()
        var = Variant.objects.get(hgvs="c.54A>G")
        self.assertEqual(var.data["counts"], {})


class TestPartialForm(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.experiment = Experiment.objects.create(
            target="test", wt_sequence="ATCG"
        )

    def make_test_data(self, scores_data=None, counts_data=None, use_exp=True):
        data = {"experiment": self.experiment.pk if use_exp else None}
        s_file, c_file = make_score_count_files(scores_data, counts_data)
        files = {Constants.SCORES_DATA: s_file}
        if c_file is not None:
            files[Constants.COUNTS_DATA] = c_file
        return data, files

    def test_new_score_upload_will_delete_old_score_data(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score\nc.50A>G,1"
        )
        form = ScoreSetForm(data=data, files=files)
        form.is_valid()
        old_model = form.save()
        old_variant = Variant.objects.all()[0]
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)

        # Now try editing the new instance
        data, files = self.make_test_data(
            scores_data="hgvs,score\nc.100A>G,1"
        )
        request = self.factory.post(
            path="/accounts/profile/edit/{}/".format(old_model.accession),
            data=data
        )
        request.user = self.alice
        request.FILES.update(files)
        form = ScoreSetForm.PartialFormFromRequest(
            request=request, instance=old_model
        )

        new_model = form.save()
        new_variant = Variant.objects.all()[0]
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)
        self.assertNotEqual(old_variant.hgvs, new_variant.hgvs)

    def test_supply_only_counts_file_results_in_error(self):
        data, files = self.make_test_data(
            scores_data="hgvs,score\nc.50A>G,1"
        )
        form = ScoreSetForm(data=data, files=files)
        form.is_valid()
        old_model = form.save()
        old_variant = Variant.objects.all()[0]
        self.assertEqual(ScoreSet.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)

        # Now try editing the new instance
        data, files = self.make_test_data(
            counts_data="hgvs,count\nc.100A>G,1"
        )
        request = self.factory.post(
            path="/accounts/profile/edit/{}/".format(old_model.accession),
            data=data
        )
        request.user = self.alice
        request.FILES.update(
            {Constants.COUNTS_DATA: files[Constants.COUNTS_DATA]}
        )
        form = ScoreSetForm.PartialFormFromRequest(
            request=request, instance=old_model
        )

        self.assertFalse(form.is_valid())
