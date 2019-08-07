import pandas as pd

from django.test import TestCase, RequestFactory
from accounts.factories import UserFactory

from main.models import Licence
from variant.factories import generate_hgvs, VariantFactory

from .. import constants
from ..factories import ExperimentFactory, ScoreSetFactory
from ..forms.scoreset import ScoreSetForm, ErrorMessages
from ..utilities import publish_dataset

from .utility import make_files


class TestScoreSetForm(TestCase):
    """
    Tests functionality of the fields specific to the ScoreSetForm.
    """

    def setUp(self):
        self.user = UserFactory()
        self.factory = RequestFactory()

    def make_post_data(
        self, score_data=None, count_data=None, meta_data=None, make_exp=True
    ):
        """
        Makes sample test input for instantiating the form to simulate
        POST data from a view. By default creates an experiment and
        assigns the class user as the administrator.

        Parameters
        ----------
        score_data : str or None
            The score file content in string format

        count_data : str, boolean or None
            The score file content in string format

        make_exp : bool
            If True, makes an experiment, otherwise leaves this as None
            
        meta_data : dict or None,
            None to use default, otherwise supply a dictionary to save as
            the extra_metadata field.
        """
        experiment = None
        if make_exp:
            experiment = ExperimentFactory()
            experiment.add_administrators(self.user)
        data = {
            "short_description": "experiment",
            "title": "title",
            "experiment": experiment.pk if experiment else None,
        }
        s_file, c_file, m_file = make_files(score_data, count_data, meta_data)
        files = {constants.variant_score_data: s_file}
        if c_file is not None:
            files[constants.variant_count_data] = c_file
        if m_file is not None:
            files[constants.meta_data] = m_file
        return data, files

    def test_licence_defaults_to_cc4(self):
        data, files = self.make_post_data()
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertTrue(form.is_valid())
        model = form.save()
        cc4 = Licence.get_default()
        self.assertEqual(model.licence, cc4)

    def test_can_set_licence_type(self):
        data, files = self.make_post_data()
        form = ScoreSetForm(data=data, files=files, user=self.user)
        data["licence"] = Licence.get_cc0().pk
        self.assertTrue(form.is_valid())
        model = form.save()
        self.assertEqual(model.licence, Licence.get_cc0())

    def test_invalid_experiment_selection_is_not_in_list(self):
        data, files = self.make_post_data()
        data["experiment"] = 100
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "not one of the available choices", form.errors["experiment"][0]
        )

    def test_can_change_experiment_on_saved_instance(self):
        data, files = self.make_post_data()
        instance = ScoreSetFactory()
        self.assertNotEqual(instance.parent.pk, data["experiment"])

        instance.parent.add_administrators(self.user)
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=instance
        )
        self.assertTrue(form.is_valid())

        instance = form.save(commit=True)
        self.assertEqual(instance.parent.pk, data["experiment"])

    def test_error_replaces_does_not_match_experiment_selection(self):
        data, files = self.make_post_data()
        new_exp = ExperimentFactory()
        new_scs = ScoreSetFactory(experiment=new_exp)
        new_scs = publish_dataset(new_scs)

        new_scs.add_administrators(self.user)
        new_exp.add_administrators(self.user)
        data["replaces"] = new_scs.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.Replaces.different_experiment,
            form.errors["replaces"][0],
        )

    def test_valid_replaces_has_not_changed_on_preexisting_instance(self):
        data, files = self.make_post_data()
        new_exp = ExperimentFactory()
        new_scs = ScoreSetFactory(experiment=new_exp)
        edit_scs = ScoreSetFactory(experiment=new_exp)

        new_scs = publish_dataset(new_scs)
        edit_scs = publish_dataset(edit_scs)

        new_scs.add_administrators(self.user)
        new_exp.add_administrators(self.user)
        edit_scs.add_administrators(self.user)

        data["experiment"] = new_exp.pk
        data["replaces"] = new_scs.pk
        form = ScoreSetForm(
            data=data, instance=edit_scs, files=files, user=self.user
        )
        self.assertTrue(form.is_valid())

    def test_admin_experiments_appear_in_options(self):
        data, files = self.make_post_data()

        # Should not appear
        viewer_exps = ExperimentFactory()
        viewer_exps.add_viewers(self.user)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields["experiment"].queryset.count(), 1)
        self.assertEqual(
            form.fields["experiment"].queryset.first().pk, data["experiment"]
        )

    def test_editor_experiments_appear_in_options(self):
        data, files = self.make_post_data(make_exp=False)

        # Should not appear
        viewer_exps = ExperimentFactory()
        viewer_exps.add_viewers(self.user)

        # Should appear
        obj1 = ExperimentFactory()
        obj1.add_editors(self.user)

        data["experiment"] = obj1.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields["experiment"].queryset.count(), 1)
        self.assertEqual(
            form.fields["experiment"].queryset.first().pk, data["experiment"]
        )

    def test_private_entries_not_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)

        # Should not appear
        obj1 = ScoreSetFactory(private=True)
        obj1.add_administrators(self.user)
        obj1.parent.add_administrators(self.user)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields["replaces"].queryset.count(), 0)

    def test_replaces_options_can_be_seeded_from_experiment(self):
        data, files = self.make_post_data(make_exp=False)

        exp = ExperimentFactory()
        exp.add_administrators(self.user)

        # Should appear
        scs = ScoreSetFactory(private=False, experiment=exp)
        scs.add_administrators(self.user)

        # Should not appear since not a member of experiment
        scs2 = ScoreSetFactory(private=False)
        scs2.add_administrators(self.user)

        form = ScoreSetForm(
            data=data, files=files, experiment=exp, user=self.user
        )
        self.assertIn(scs, form.fields["replaces"].queryset)
        self.assertNotIn(scs2, form.fields["replaces"].queryset)

    def test_experiment_options_frozen_when_passing_experiment_instance(self):
        data, files = self.make_post_data(make_exp=False)

        exp = ExperimentFactory()
        exp.add_administrators(self.user)

        # Should not appear since locked to above
        exp2 = ExperimentFactory()
        exp2.add_administrators(self.user)

        form = ScoreSetForm(
            data=data, files=files, experiment=exp, user=self.user
        )
        self.assertIn(exp, form.fields["experiment"].queryset)
        self.assertNotIn(exp2, form.fields["experiment"].queryset)

    def test_admin_scoresets_appear_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        exp = ExperimentFactory()
        exp.add_administrators(self.user)
        scs = ScoreSetFactory(private=False, experiment=exp)
        scs.add_administrators(self.user)

        # Should not appear
        scs2 = ScoreSetFactory(private=False, experiment=exp)
        scs2.add_viewers(self.user)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields["replaces"].queryset.count(), 1)
        self.assertEqual(form.fields["replaces"].queryset.first().pk, scs.pk)

    def test_editor_scoresets_appear_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        exp = ExperimentFactory()
        exp.add_editors(self.user)
        scs = ScoreSetFactory(private=False, experiment=exp)
        scs.add_editors(self.user)

        # should not appear
        scs2 = ScoreSetFactory(private=False, experiment=exp)
        scs2.add_viewers(self.user)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields["replaces"].queryset.count(), 1)
        self.assertEqual(form.fields["replaces"].queryset.first().pk, scs.pk)

    def test_viewer_scoresets_do_not_appear_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        obj1 = ScoreSetFactory(private=False)

        obj1.add_viewers(self.user)
        obj1.parent.parent.add_viewers(self.user)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields["replaces"].queryset.count(), 0)

    def test_invalid_different_variants_in_score_and_count_files(self):
        score_hgvs = generate_hgvs()
        count_hgvs = generate_hgvs()
        scores = "{},{}\n{},1.0".format(
            constants.hgvs_nt_column,
            constants.required_score_column,
            score_hgvs,
        )

        # Generate a unique count hgvs variant.
        while count_hgvs == score_hgvs:
            count_hgvs = generate_hgvs()
        counts = "{},{}\n{},2.0".format(
            constants.hgvs_nt_column, "count", count_hgvs
        )

        data, files = self.make_post_data(scores, counts)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())

    def test_invalid_no_score_file(self):
        data, files = self.make_post_data()
        files.pop(constants.variant_score_data)
        form = ScoreSetForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.ScoreData.score_file_required,
            form.errors["score_data"][0],
        )

    def test_valid_no_score_file_when_instance_supplied(self):
        data, files = self.make_post_data()
        files.pop(constants.variant_score_data)

        instance = ScoreSetFactory()
        VariantFactory(scoreset=instance)
        instance.experiment.add_administrators(self.user)
        data["experiment"] = instance.experiment.pk

        form = ScoreSetForm(data=data, user=self.user, instance=instance)
        self.assertTrue(form.is_valid())

    def test_invalid_no_score_file_and_instance_is_in_fail_state(self):
        data, files = self.make_post_data()
        files.pop(constants.variant_score_data)

        instance = ScoreSetFactory()
        instance.processing_state = constants.failed
        instance.save()
        instance.experiment.add_administrators(self.user)
        data["experiment"] = instance.experiment.pk

        form = ScoreSetForm(data=data, user=self.user, instance=instance)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.ScoreData.score_file_required,
            form.errors["score_data"][0],
        )

    def test_uploads_disabled_instance_in_processing_state(self):
        instance = ScoreSetFactory()
        instance.processing_state = constants.processing
        instance.save()

        form = ScoreSetForm(user=self.user, instance=instance)
        self.assertTrue(form.fields["score_data"].disabled)
        self.assertTrue(form.fields["count_data"].disabled)

    def test_invalid_no_scores_but_counts_provided(self):
        data, files = self.make_post_data(count_data=True)
        files.pop(constants.variant_score_data)
        instance = ScoreSetFactory()
        VariantFactory(scoreset=instance)
        instance.experiment.add_administrators(self.user)
        data["experiment"] = instance.experiment.pk

        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=instance
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.CountData.no_score_file, form.errors["score_data"][0]
        )

    def test_invalid_empty_score_file(self):
        score_data = "{},{},se\n".format(
            constants.hgvs_nt_column, constants.required_score_column
        )
        data, files = self.make_post_data(score_data)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.ScoreData.no_variants, form.errors["score_data"][0]
        )

    def test_serialize_variants_returns_empty_frames_and_index(self):
        form = ScoreSetForm(data={}, user=self.user)
        form.is_valid()
        sdf, cdf, index = form.serialize_variants()
        self.assertTrue(sdf.empty)
        self.assertTrue(cdf.empty)
        self.assertIsNone(index)

    def test_serialize_variants_returns_dfs_and_scores_primary_hgvs(self):
        scs = ScoreSetFactory()
        data, files = self.make_post_data(count_data=True)
        data["experiment"] = scs.experiment.pk
        scs.experiment.add_administrators(self.user)
        scs.add_administrators(self.user)
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=scs
        )
        self.assertTrue(form.is_valid())

        sdf, cdf, index = form.serialize_variants()
        self.assertIsInstance(sdf, pd.DataFrame)
        self.assertEqual(len(sdf), 1)

        self.assertIsInstance(cdf, pd.DataFrame)
        self.assertEqual(len(cdf), 1)

        self.assertEqual(index, constants.hgvs_nt_column)

    def test_new_scores_resets_dataset_columns(self):
        scs = ScoreSetFactory()
        for i in range(5):
            VariantFactory(scoreset=scs)
        self.assertEqual(scs.children.count(), 5)

        data, files = self.make_post_data()
        data["experiment"] = scs.experiment.pk
        scs.experiment.add_administrators(self.user)
        scs.add_administrators(self.user)
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=scs
        )
        self.assertTrue(form.is_valid())

        form.save(commit=True)
        self.assertEqual(
            sorted(form.dataset_columns[constants.score_columns]),
            sorted(["score", "se"]),
        )

    def test_form_invalid_when_invalid_metadata_file_supplied(self):
        data, files = self.make_post_data(meta_data="{not valid}")
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            ErrorMessages.MetaData.incorrect_format[:-4],
            form.errors["meta_data"][0],
        )

    def test_valid_meta(self):
        dict_ = {"foo": ["bar"]}
        data, files = self.make_post_data(meta_data=dict_)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertTrue(form.is_valid())
        model = form.save()
        result = model.extra_metadata
        self.assertEqual(result, dict_)

    def test_cannot_replace_scoreset_that_is_already_replaced(self):
        scs1 = ScoreSetFactory(private=False)
        scs2 = ScoreSetFactory(
            private=False, experiment=scs1.parent, replaces=scs1
        )
        scs1.add_administrators(self.user)
        scs1.parent.add_administrators(self.user)
        scs2.add_administrators(self.user)

        data, files = self.make_post_data(make_exp=False)
        data["replaces"] = scs1.pk
        data["experiment"] = scs1.parent.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            ErrorMessages.Replaces.already_replaced[3:],
            form.errors["replaces"][0],
        )

    def test_cannot_replace_a_private_scoreset(self):
        scs1 = ScoreSetFactory(private=True)
        scs1.add_administrators(self.user)
        scs1.parent.add_administrators(self.user)

        data, files = self.make_post_data(make_exp=False)
        data["replaces"] = scs1.pk
        data["experiment"] = scs1.parent.pk

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.Field.invalid_choice, form.errors["replaces"][0]
        )

    def test_form_scoreset_instance_not_in_replace_options(self):
        scs = ScoreSetFactory(private=False)
        data, files = self.make_post_data()

        scs.add_administrators(self.user)
        scs.parent.add_administrators(self.user)

        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=scs
        )
        self.assertNotIn(scs, form.fields["replaces"].queryset.all())

    def test_cant_replace_self(self):
        scs1 = ScoreSetFactory(private=False)
        scs1.add_administrators(self.user)
        scs1.parent.add_administrators(self.user)

        data, files = self.make_post_data(make_exp=False)
        data["replaces"] = scs1.pk
        data["experiment"] = scs1.parent.pk

        form = ScoreSetForm(
            data=data, files=files, instance=scs1, user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.Field.invalid_choice, form.errors["replaces"][0]
        )

    def test_changing_experiment_sets_replaces_to_none(self):
        exp1 = ExperimentFactory()
        exp2 = ExperimentFactory()
        replaced = ScoreSetFactory(experiment=exp1)
        obj = ScoreSetFactory(experiment=exp1, replaces=replaced)
        self.assertEqual(obj.replaces, replaced)
        self.assertEqual(replaced.replaced_by, obj)

        exp1.add_administrators(self.user)
        exp2.add_administrators(self.user)
        replaced.add_administrators(self.user)
        obj.add_administrators(self.user)

        data, files = self.make_post_data()
        data["experiment"] = exp2.pk
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=obj
        )
        self.assertTrue(form.is_valid())
        instance = form.save(commit=True)
        self.assertIsNone(instance.replaces)
        self.assertIsNone(replaced.next_version)
        self.assertEqual(exp2.urn, instance.parent.urn)

    def test_invalid_set_replaces_that_is_not_member_of_a_changed_experiment(
        self
    ):
        exp = ExperimentFactory()
        obj = ScoreSetFactory(experiment=exp)
        replaced = ScoreSetFactory(experiment=exp, private=False)

        exp.add_administrators(self.user)
        replaced.add_administrators(self.user)
        obj.add_administrators(self.user)

        # Make the data, which also sets the selected experiment
        data, files = self.make_post_data()
        # Set the replaces to an option not in the selected experiment
        data["replaces"] = replaced.pk
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=obj
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.Replaces.different_experiment,
            form.errors["replaces"][0],
        )

    def test_invalid_change_experiment_public_scoreset(self):
        obj = ScoreSetFactory()
        obj.parent.add_administrators(self.user)
        obj.add_administrators(self.user)
        obj = publish_dataset(obj)

        # Make the data, which also sets the selected experiment
        data, files = self.make_post_data()
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=obj
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            ErrorMessages.Experiment.public_scoreset,
            form.errors["experiment"][0],
        )

    def test_from_request_modifies_existing_instance(self):
        scs = ScoreSetFactory()
        scs.add_administrators(self.user)
        scs.parent.add_administrators(self.user)
        VariantFactory(
            scoreset=scs
        )  # Create variant to bypass the file upload

        data, files = self.make_post_data(make_exp=True)
        request = self.factory.post("/path/", data=data, files=files)
        request.user = self.user

        form = ScoreSetForm.from_request(request, scs)
        instance = form.save(commit=True)
        self.assertEqual(instance.parent.pk, data["experiment"])
        self.assertEqual(instance.get_title(), data["title"])
        self.assertEqual(instance.get_description(), data["short_description"])

    def test_has_variants_returns_true_when_files_uploaded(self):
        data, files = self.make_post_data()
        instance = ScoreSetFactory()
        instance.parent.add_administrators(self.user)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.has_variants())

    def test_form_has_variants_is_false_when_no_files_uploaded_and_scoreset_has_variants(
        self
    ):
        data, files = self.make_post_data()
        instance = ScoreSetFactory()
        for _ in range(5):
            VariantFactory(scoreset=instance)

        instance.parent.add_administrators(self.user)
        form = ScoreSetForm(data=data, user=self.user, instance=instance)

        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_variants())

    def test_invalid_form_no_variants_on_existing_scoreset_and_no_files_uploaded(
        self
    ):
        data, files = self.make_post_data()
        instance = ScoreSetFactory()
        instance.parent.add_administrators(self.user)
        form = ScoreSetForm(data=data, user=self.user, instance=instance)

        self.assertFalse(form.is_valid())
        self.assertFalse(form.has_variants())

    def test_valid_form_variants_on_existing_scoreset_and_no_files_uploaded(
        self
    ):
        data, files = self.make_post_data()
        instance = ScoreSetFactory()
        for _ in range(5):
            VariantFactory(scoreset=instance)

        instance.parent.add_administrators(self.user)
        form = ScoreSetForm(data=data, user=self.user, instance=instance)

        self.assertTrue(form.is_valid())
        self.assertFalse(form.has_variants())
