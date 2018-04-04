from django.http import QueryDict
from django.test import TestCase

from accounts.factories import UserFactory

from ..factories import ExperimentFactory, ExperimentSetFactory
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

    def test_pops_target_organism(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(data={}, user=self.user, instance=obj)
        self.assertNotIn('target_organism', form.fields)

    def test_pops_target(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(data={}, user=self.user, instance=obj)
        self.assertNotIn('target', form.fields)

    def test_pops_wt_sequence(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(data={}, user=self.user, instance=obj)
        self.assertNotIn('wt_sequence', form.fields)

    def test_pops_experimentset(self):
        obj = ExperimentFactory()
        form = ExperimentEditForm(data={}, user=self.user, instance=obj)
        self.assertNotIn('experimentset', form.fields)

    def test_cannot_save_popped_field(self):
        obj = ExperimentFactory()
        old_target = obj.target
        old_sequence = obj.wt_sequence
        old_exps = obj.experimentset.pk

        form = ExperimentEditForm(
            data={
                'target_organism': ['protein'],
                'wt_sequence': 'aaaa',
                'target': 'human',
                'experimentset': 1
            },
            user=self.user, instance=obj
        )
        instance = form.save(commit=True)
        self.assertEqual(instance.target_organism.count(), 0)
        self.assertEqual(instance.target, old_target)
        self.assertEqual(instance.wt_sequence, old_sequence)
        self.assertEqual(instance.experimentset.pk, old_exps)
