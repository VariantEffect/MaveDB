from django.test import TestCase, RequestFactory, mock
from django.core.exceptions import ValidationError
from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_viewer,
    assign_user_as_instance_editor,
    assign_user_as_instance_admin
)
from main.models import Licence
from variant.models import Variant
from variant.factories import generate_hgvs, VariantFactory

import dataset.constants as constants

from ..factories import ExperimentFactory, ScoreSetFactory
from ..forms.scoreset import ScoreSetForm

from .utility import make_files


class TestScoreSetForm(TestCase):
    """
    Tests functionality of the fields specific to the ScoreSetForm.
    """
    def setUp(self):
        self.user = UserFactory()
        self.factory = RequestFactory()

    def make_post_data(self, score_data=None, count_data=None,
                       meta_data=None, make_exp=True):
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
        """
        experiment = None
        if make_exp:
            experiment = ExperimentFactory()
            assign_user_as_instance_admin(self.user, experiment)
        data = {
            'short_description': 'experiment',
            'title': 'title',
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

    def test_not_valid_experiment_selection_is_not_in_list(self):
        data, files = self.make_post_data()
        data["experiment"] = 100
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())

    def test_variants_are_saved_via_m2m_relationship(self):
        data, files = self.make_post_data()
        form = ScoreSetForm(data=data, files=files, user=self.user)
        instance = form.save(commit=True)
        self.assertEqual(instance.variants.count(), 1)

    def test_not_valid_change_experiment_from_saved_instance(self):
        data, files = self.make_post_data()  # new experiment
        inst = ScoreSetFactory()
        assign_user_as_instance_admin(self.user, inst.parent)
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=inst)
        self.assertFalse(form.is_valid())

    def test_error_replaces_does_not_match_experiment_selection(self):
        data, files = self.make_post_data()
        new_exp = ExperimentFactory()
        new_scs = ScoreSetFactory(experiment=new_exp)

        assign_user_as_instance_admin(self.user, new_scs)
        assign_user_as_instance_admin(self.user, new_exp)
        data["replaces"] = new_scs.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())

    def test_admin_experiments_appear_in_options(self):
        data, files = self.make_post_data()
        assign_user_as_instance_viewer(self.user, ExperimentFactory())
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['experiment'].queryset.count(), 1)
        self.assertEqual(
            form.fields['experiment'].queryset.first().pk,
            data['experiment'])

    def test_editor_experiments_appear_in_options(self):
        data, files = self.make_post_data(make_exp=False)
        obj1 = ExperimentFactory()

        assign_user_as_instance_editor(self.user, obj1)
        assign_user_as_instance_viewer(self.user, ExperimentFactory())
        data['experiment'] = obj1.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['experiment'].queryset.count(), 1)
        self.assertEqual(
            form.fields['experiment'].queryset.first().pk,
            data['experiment']
        )

    def test_private_entries_not_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        obj1 = ScoreSetFactory(private=True)
        assign_user_as_instance_admin(self.user, obj1)
        assign_user_as_instance_admin(self.user, obj1.parent)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['replaces'].queryset.count(), 0)

    def test_replaces_options_can_be_seeded_from_experiment(self):
        data, files = self.make_post_data(make_exp=False)
        exp = ExperimentFactory()
        scs = ScoreSetFactory(private=False, experiment=exp)
        scs2 = ScoreSetFactory()
        assign_user_as_instance_admin(self.user, exp)
        assign_user_as_instance_admin(self.user, scs)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['replaces'].queryset.count(), 1)
        self.assertEqual(
            form.fields['replaces'].queryset.first().pk, scs.pk)

    def test_admin_scoresets_appear_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        exp = ExperimentFactory()
        scs = ScoreSetFactory(private=False, experiment=exp)
        _ = ScoreSetFactory(private=False, experiment=exp)
        assign_user_as_instance_admin(self.user, exp)
        assign_user_as_instance_admin(self.user, scs)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['replaces'].queryset.count(), 1)
        self.assertEqual(
            form.fields['replaces'].queryset.first().pk, scs.pk)

    def test_editor_scoresets_appear_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        exp = ExperimentFactory()
        scs = ScoreSetFactory(private=False, experiment=exp)
        _ = ScoreSetFactory(private=False, experiment=exp)
        assign_user_as_instance_editor(self.user, exp)
        assign_user_as_instance_editor(self.user, scs)

        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['replaces'].queryset.count(), 1)
        self.assertEqual(
            form.fields['replaces'].queryset.first().pk, scs.pk)

    def test_viewer_scoresets_do_not_appear_in_replaces_options(self):
        data, files = self.make_post_data(make_exp=False)
        obj1 = ScoreSetFactory(private=False)
        assign_user_as_instance_viewer(self.user, obj1)
        assign_user_as_instance_viewer(self.user, obj1.parent)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertEqual(form.fields['replaces'].queryset.count(), 0)

    def test_from_request_locks_experiment_to_instance_experiment(self):
        inst = ScoreSetFactory()
        data, files = self.make_post_data()
        request = self.factory.post('/path/', data=data)
        request.user = self.user
        form = ScoreSetForm.from_request(request, inst)
        self.assertEqual(
            form.fields['experiment'].initial, inst.experiment)
        self.assertEqual(
            form.fields['experiment'].queryset.count(), 1)
        self.assertIn(
            inst.experiment, form.fields['experiment'].queryset)

    def test_variant_data_is_cross_populated_with_nones(self):
        score_hgvs = generate_hgvs()
        count_hgvs = generate_hgvs()
        scores = "{},{}\n{},1.0".format(
            constants.hgvs_column, constants.required_score_column, score_hgvs)
        while count_hgvs == score_hgvs:
            count_hgvs = generate_hgvs()
        counts = "{},{}\n{},2.0".format(
            constants.hgvs_column, 'count', count_hgvs)
        data, files = self.make_post_data(scores, counts)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertTrue(form.is_valid())
        variants = form.get_variants()

        # Check score data parsed correctly
        self.assertEqual(
            1.0,
            variants[score_hgvs].data[constants.variant_score_data][
                constants.required_score_column
            ])
        # Check count data for score_hgvs is set to None
        self.assertIsNone(
            variants[score_hgvs].data[constants.variant_count_data]['count'])

        # Check count data parsed correctly
        self.assertEqual(
            2.0,
            variants[count_hgvs].data[constants.variant_count_data]['count'])
        # Check score data for count_hgvs is set to None
        self.assertIsNone(
            variants[count_hgvs].data[constants.variant_score_data][
                constants.required_score_column])

    def test_invalid_no_score_file(self):
        data, files = self.make_post_data()
        files.pop(constants.variant_score_data)
        form = ScoreSetForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())

    def test_valid_no_score_file_when_instance_supplied(self):
        data, files = self.make_post_data()
        files.pop(constants.variant_score_data)

        instance = ScoreSetFactory()
        assign_user_as_instance_admin(self.user, instance.experiment)
        data['experiment'] = instance.experiment.pk

        form = ScoreSetForm(
            data=data, user=self.user, instance=instance)
        self.assertTrue(form.is_valid())

    def test_invalid_no_scores_but_counts_provided(self):
        data, files = self.make_post_data(count_data=True)
        files.pop(constants.variant_score_data)
        instance = ScoreSetFactory()
        assign_user_as_instance_admin(self.user, instance.experiment)
        data['experiment'] = instance.experiment.pk

        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=instance)
        self.assertFalse(form.is_valid())

    def test_variants_correctly_parsed_integration_test(self):
        # Generate distinct hgvs strings
        score_hgvs = generate_hgvs()
        count_hgvs = generate_hgvs()
        while count_hgvs == score_hgvs:
            count_hgvs = generate_hgvs()

        score_data = "{},{},se\n{},1,".format(
            constants.hgvs_column, constants.required_score_column, score_hgvs
        )
        count_data = "{},{},sig\n{},None,-1".format(
            constants.hgvs_column, 'count', count_hgvs
        )
        data, files = self.make_post_data(score_data, count_data)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        scs = form.save(commit=True)
        variants = scs.children

        data_1 = {
            'score_data': {'se': None, 'score': 1.0},
            'count_data': {'sig': None, 'count': None},
        }
        data_2 = {
            'score_data': {'se': None, 'score': None},
            'count_data': {'sig': -1.0, 'count': None},
        }
        self.assertEqual(variants.filter(hgvs=score_hgvs).first().data, data_1)
        self.assertEqual(variants.filter(hgvs=count_hgvs).first().data, data_2)

    def test_invalid_empty_score_file(self):
        score_data = "{},{},se\n".format(
            constants.hgvs_column, constants.required_score_column
        )
        data, files = self.make_post_data(score_data)
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())
        
    def test_new_scores_deletes_variants(self):
        scs = ScoreSetFactory()
        for i in range(5):
            VariantFactory(scoreset=scs)
        self.assertEqual(scs.children.count(), 5)

        data, files = self.make_post_data()
        data['experiment'] = scs.experiment.pk
        assign_user_as_instance_admin(self.user, scs.experiment)
        assign_user_as_instance_admin(self.user, scs)
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=scs)
        self.assertTrue(form.is_valid())

        form.save(commit=True)

        scs.refresh_from_db()
        self.assertTrue(Variant.objects.count(), 1)
        self.assertTrue(scs.children.count(), 1)
        self.assertTrue(scs.last_child_value, 1)
        self.assertEqual(
            sorted(scs.dataset_columns[constants.score_columns]),
            sorted(['score', 'se'])
        )

    def test_invalid_dataset_columns_do_not_match_variant_columns(self):
        data, files = self.make_post_data()
        form = ScoreSetForm(data=data, files=files, user=self.user)
        form.clean()
        form.dataset_columns = {
            constants.score_columns: [constants.required_score_column, 'aaa'],
            constants.count_columns: [],
        }
        with self.assertRaises(ValidationError):
            form.clean()
    
    def test_ve_invalid_meta(self):
        data, files = self.make_post_data(meta_data="{not valid}")
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())

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
            private=False, experiment=scs1.parent, replaces=scs1)
        assign_user_as_instance_admin(self.user, scs1)
        assign_user_as_instance_admin(self.user, scs2)
        assign_user_as_instance_admin(self.user, scs1.parent)

        data, files = self.make_post_data(make_exp=False)
        data['replaces'] = scs1.pk
        data['experiment'] = scs1.parent.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())

    def test_cannot_replace_a_private_scoreset(self):
        scs1 = ScoreSetFactory(private=True)
        assign_user_as_instance_admin(self.user, scs1)
        assign_user_as_instance_admin(self.user, scs1.parent)

        data, files = self.make_post_data(make_exp=False)
        data['replaces'] = scs1.pk
        data['experiment'] = scs1.parent.pk
        form = ScoreSetForm(data=data, files=files, user=self.user)
        self.assertFalse(form.is_valid())

    def test_form_scoreset_instance_not_in_replace_options(self):
        scs = ScoreSetFactory(private=False)
        data, files = self.make_post_data()
        assign_user_as_instance_admin(self.user, scs.experiment)
        assign_user_as_instance_admin(self.user, scs)
        form = ScoreSetForm(
            data=data, files=files, user=self.user, instance=scs)
        self.assertNotIn(scs, form.fields['replaces'].queryset.all())

    def test_cant_replace_self(self):
        scs1 = ScoreSetFactory(private=False)
        assign_user_as_instance_admin(self.user, scs1)
        assign_user_as_instance_admin(self.user, scs1.parent)
        data, files = self.make_post_data(make_exp=False)
        data['replaces'] = scs1.pk
        data['experiment'] = scs1.parent.pk
        form = ScoreSetForm(
            data=data, files=files, instance=scs1, user=self.user)
        self.assertFalse(form.is_valid())
    
    def test_save_can_publish_propagates_modified_by(self):
        self.fail()
        
    def test_save_can_publish_propagates_private_bit(self):
        self.fail()
        
    def test_save_with_publish_false_does_not_propagate_or_set_public(self):
        self.fail()
