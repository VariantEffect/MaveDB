from django.test import TestCase
from django.contrib.auth import get_user_model

from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet

from ..serializers import (
    ExperimentSerializer,
    ExperimentSetSerializer,
    ScoreSetSerializer,
    UserSerializer
)

User = get_user_model()


class TestExperimentSetSerializer(TestCase):

    def test_json_has_correct_keys(self):
        self.fail("Write this test.")

    def test_empty_json_object_not_found(self):
        self.fail("Write this test.")

    def test_empty_list_not_experiments(self):
        self.fail("Write this test.")

    def test_can_serialize_queryset(self):
        self.fail("Write this test.")
