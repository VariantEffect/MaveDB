from django.test import TestCase

from accounts.factories import UserFactory

from ..factories import ExperimentFactory
from ..forms.experiment import ExperimentEditForm


class TestExperimentEditForm(TestCase):
    """
    Test the functionality of the subclassed edit form.
    """
    def setUp(self):
        self.user = UserFactory()

    def test_empty_data_submission_is_valid(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(data={}, user=self.user, instance=obj)
        self.assertTrue(form.is_valid())

    def test_pops_experimentset(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(data={}, user=self.user, instance=obj)
        self.assertNotIn('experimentset', form.fields)

    def test_cannot_save_popped_field(self):
        obj = ExperimentFactory()
        old_exps = obj.experimentset.pk

        form = ExperimentEditForm(
            data={
                'experimentset': 1
            },
            user=self.user, instance=obj
        )
        instance = form.save(commit=True)
        self.assertEqual(instance.experimentset.pk, old_exps)
