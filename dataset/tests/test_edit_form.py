from django.http import QueryDict
from django.test import TestCase

from ..models import Experiment
from ..forms import ExperimentEditForm


class TestScoreSetEditForm(TestCase):

    @staticmethod
    def experiment():
        return Experiment.objects.create(
            target="test", wt_sequence="ATCG"
        )

    def test_can_instantiate_form_with_instance(self):
        instance = self.experiment()
        form = ExperimentEditForm({}, instance=instance)
        self.assertTrue(form.is_valid())

    def test_can_save_new_data(self):
        instance = self.experiment()
        post = QueryDict('', mutable=True)
        post.setlist("keywords", ["test"])
        post.setlist("external_accessions", ["test"])
        form = ExperimentEditForm(post, instance=instance)
        instance = form.save(commit=True)
        self.assertEqual(instance.keywords.count(), 1)
        self.assertEqual(instance.external_accessions.count(), 1)

    def test_save_does_not_alter_other_fields(self):
        instance = self.experiment()
        post = QueryDict('', mutable=True)
        post.setlist("wt_sequence", 'gggg')
        form = ExperimentEditForm(post, instance=instance)
        instance = form.save(commit=True)
        self.assertEqual(instance.wt_sequence, 'ATCG')

    def test_cannot_save_target_organism(self):
        instance = self.experiment()
        post = QueryDict('', mutable=True)
        post.setlist("target_organism", 'homo sapien')
        form = ExperimentEditForm(post, instance=instance)
        instance = form.save(commit=True)
        self.assertEqual(instance.target_organism.count(), 0)
