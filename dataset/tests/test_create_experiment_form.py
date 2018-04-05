from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer
)

from ..factories import ExperimentFactory, ExperimentSetFactory
from ..forms.experiment import ExperimentForm
from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet


class TestExperimentForm(TestCase):
    """
    Test that the `ExperimentForm` object is able to raise the appropriate
    `ValidationError` on fields such as experimentset and wt_sequence.
    """
    def setUp(self):
        self.user = UserFactory()
        self.factory = RequestFactory()

    @staticmethod
    def make_form_data(target='BRCA1', wt_sequence='ATCG', use_exps=False):
        """
        Makes sample test input for instantiating the form to simulate
        POST data from a view.

        Parameters
        ----------
        target : str or None
            The gene target

        wt_sequence : str or None
            The wildtype sequence

        use_exps : bool
            If True, experimentset is set to None
        """
        data = {
            "target": target,
            "wt_sequence": wt_sequence,
            "experimentset": (
                None if not use_exps else ExperimentSetFactory().pk
            )
        }
        return data

    def test_can_create_form_and_save_new_instance(self):
        form = ExperimentForm(user=self.user, data=self.make_form_data())
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(Experiment.objects.count(), 1)
        self.assertEqual(ExperimentSet.objects.count(), 1)

    def test_not_valid_empty_target(self):
        data = self.make_form_data(target='')
        form = ExperimentForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

        data = self.make_form_data(target=None)
        form = ExperimentForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_not_valid_empty_wildtype(self):
        data = self.make_form_data(wt_sequence='')
        form = ExperimentForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

        data = self.make_form_data(wt_sequence=None)
        form = ExperimentForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_not_valid_non_dna_wildtype(self):
        data = self.make_form_data(wt_sequence='not dna')
        form = ExperimentForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_not_valid_experimentset_not_found(self):
        data = self.make_form_data()
        data["experimentset"] = "blah"
        form = ExperimentForm(user=self.user, data=data)
        self.assertFalse(form.is_valid())

    def test_can_create_new_target_organisms(self):
        data = self.make_form_data()
        data["target_organism"] = "human"
        form = ExperimentForm(user=self.user, data=data)
        instance = form.save(commit=True)
        self.assertEqual(instance.target_organism.count(), 1)

    def test_does_not_save_duplicated_target_organisms(self):
        data = self.make_form_data()
        data['target_organism'] = ['human', 'human']
        form = ExperimentForm(user=self.user, data=data)
        instance = form.save(commit=True)
        self.assertEqual(instance.target_organism.count(), 1)

    def test_admin_experimentset_appear_in_options(self):
        obj1 = ExperimentSetFactory()
        _ = ExperimentSetFactory()
        assign_user_as_instance_admin(self.user, obj1)
        form = ExperimentForm(user=self.user)
        self.assertEqual(form.fields['experimentset'].queryset.count(), 1)
        self.assertEqual(form.fields['experimentset'].queryset.first(), obj1)

    def test_contributor_experimentset_appear_in_options(self):
        obj1 = ExperimentSetFactory()
        _ = ExperimentSetFactory()
        assign_user_as_instance_contributor(self.user, obj1)
        form = ExperimentForm(user=self.user)
        self.assertEqual(form.fields['experimentset'].queryset.count(), 1)
        self.assertEqual(form.fields['experimentset'].queryset.first(), obj1)

    def test_viewer_experimentset_do_not_appear_in_options(self):
        obj1 = ExperimentSetFactory()
        assign_user_as_instance_viewer(self.user, obj1)
        form = ExperimentForm(user=self.user)
        self.assertEqual(form.fields['experimentset'].queryset.count(), 0)

    def test_from_request_modifies_existing_instance(self):
        exp = ExperimentFactory()
        data = self.make_form_data(use_exps=False)
        data['experimentset'] = exp.experimentset.pk
        request = self.factory.post('/path/', data=data)
        request.user = self.user
        form = ExperimentForm.from_request(request, exp)
        form.save(commit=True)
        self.assertEqual(
            form.instance.wt_sequence, data['wt_sequence'])
        self.assertEqual(
            form.instance.experimentset.pk, data['experimentset'])

    def test_from_request_locks_experimentset_to_instance_experimentset(self):
        exp = ExperimentFactory()
        data = self.make_form_data(use_exps=False)
        data['experimentset'] = exp.experimentset.pk
        request = self.factory.post('/path/', data=data)
        request.user = self.user
        form = ExperimentForm.from_request(request, exp)
        self.assertEqual(
            form.fields['experimentset'].initial, exp.experimentset)
        self.assertEqual(
            form.fields['experimentset'].queryset.count(), 1)
        self.assertIn(
            exp.experimentset, form.fields['experimentset'].queryset)

    def test_not_valid_change_experimentset_from_saved_instance(self):
        exp = ExperimentFactory()
        data = self.make_form_data(use_exps=False)  # None experimentset
        request = self.factory.post('/path/', data=data)
        request.user = self.user
        form = ExperimentForm.from_request(request, exp)
        self.assertFalse(form.is_valid())

        data = self.make_form_data()  # New experimentset
        request = self.factory.post('/path/', data=data)
        request.user = self.user
        form = ExperimentForm.from_request(request, exp)
        self.assertFalse(form.is_valid())
