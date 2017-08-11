
from django.test import TestCase, TransactionTestCase

from experiment.models import Experiment, ExperimentSet


class TestExperimentView(TransactionTestCase):

    reset_sequences = True

    def test_uses_correct_template(self):
        e = Experiment.objects.create(target="test", wt_sequence="atcg")
        response = self.client.get('/experiment/{}/'.format(e.accession))
        self.assertTemplateUsed(response, 'experiment/experiment.html')
