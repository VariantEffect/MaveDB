from django.test import TestCase

from accounts.factories import UserFactory

from ..factories import ExperimentFactory
from ..forms.experiment import ExperimentEditForm


class TestExperimentEditForm(TestCase):
    """
    Test the functionality of the subclassed edit form.
    """

    @staticmethod
    def make_form_data():
        """
        Makes sample test input for instantiating the form to simulate
        POST data from a view.
        """
        data = {"short_description": "experiment", "title": "title"}
        return data

    def setUp(self):
        self.user = UserFactory()

    def test_empty_data_submission_is_valid(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(
            data=self.make_form_data(), user=self.user, instance=obj
        )
        self.assertTrue(form.is_valid())

    def test_pops_experimentset(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(
            data=self.make_form_data(), user=self.user, instance=obj
        )
        self.assertNotIn("experimentset", form.fields)

    def test_cannot_save_popped_field(self):
        obj = ExperimentFactory()
        old_exps = obj.experimentset.pk

        data = self.make_form_data()
        data["experimentset"] = 1
        form = ExperimentEditForm(data=data, user=self.user, instance=obj)
        instance = form.save(commit=True)
        self.assertEqual(instance.experimentset.pk, old_exps)
