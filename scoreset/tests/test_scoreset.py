import datetime

from django.db import IntegrityError
from django.test import TestCase

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet


class TestExperiment(TestCase):
    """
    The purpose of this unit test is to test that the database model
    :py:class:`ScoreSet`, representing an experiment with associated
    :py:class:`Variant` objects. We will test correctness of creation,
    validation, uniqueness, queries and that the appropriate errors are raised.
    """
    def setUp(self):
        self.expset = ExperimentSet.objects.create(
            accession=ExperimentSet.build_accession())
        self.target = "target"
        self.wt_seq = "ATCG"
        self.exp_1 = Experiment.objects.create(
            accession=Experiment.build_accession(self.expset),
            experimentset=self.expset,
            target=self.target, wt_sequence=self.wt_seq)
        self.exp_2 = Experiment.objects.create(
            accession=Experiment.build_accession(self.expset),
            experimentset=self.expset,
            target=self.target, wt_sequence=self.wt_seq)
