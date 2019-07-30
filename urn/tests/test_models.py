import random

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from dataset import models
from dataset.factories import (
    ScoreSetFactory,
    ExperimentFactory,
    ExperimentSetFactory,
)
from variant.models import Variant
from variant.factories import VariantFactory


from ..models import get_model_by_urn


class TestGetByUrn(TestCase):
    def test_can_return_scoreset(self):
        obj = ScoreSetFactory()
        self.assertIsInstance(
            get_model_by_urn(obj.urn), models.scoreset.ScoreSet
        )

    def test_can_return_experiment(self):
        obj = ExperimentFactory()
        self.assertIsInstance(
            get_model_by_urn(obj.urn), models.experiment.Experiment
        )

    def test_can_return_experimentset(self):
        obj = ExperimentSetFactory()
        self.assertIsInstance(
            get_model_by_urn(obj.urn), models.experimentset.ExperimentSet
        )

    def test_can_return_variant(self):
        obj = VariantFactory()
        self.assertIsInstance(get_model_by_urn(obj.urn), Variant)

    def test_ObjectDoesNotExist_if_cannot_find_urn(self):
        with self.assertRaises(ObjectDoesNotExist):
            self.assertIsInstance(get_model_by_urn("urn:111"), Variant)

    def test_will_avoid_tmp_urn_collision(self):
        random.seed(0)
        obj1 = ExperimentSetFactory(private=True)
        random.seed(0)
        obj2 = ExperimentSetFactory(private=True)
        self.assertNotEqual(obj1.urn, obj2.urn)
