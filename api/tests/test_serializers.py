from django.test import TestCase
from django.contrib.auth import get_user_model

from main.models import Licence
from accounts.permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer
)

import dataset.constants as constants
from dataset.models import Experiment, ExperimentSet, ScoreSet

from ..serializers import (
    ExperimentSerializer,
    ExperimentSetSerializer,
    ScoreSetSerializer,
    UserSerializer
)

User = get_user_model()


def make_experimentset():
    return ExperimentSet.objects.create()


def make_experiment(experimentset=None):
    return Experiment.objects.create(
        experimentset=experimentset,
        target="test", wt_sequence="AT"
    )


def make_scoreset(experiment=None, replaces=None):
    if not experiment:
        experiment = make_experiment()
    scs = ScoreSet.objects.create(experiment=experiment, replaces=replaces)
    scs.licence = Licence.get_default()
    scs.save()
    return scs


class TestExperimentSetSerializer(TestCase):

    def test_can_correctly_serialize_instance(self):
        experiment = make_experiment()
        instance = experiment.experimentset

        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(alice, instance)
        assign_user_as_instance_viewer(bob, instance)

        experiment.publish(alice)
        instance.publish(alice)

        serializer = ExperimentSetSerializer()
        expected = {
            "contributors": ["alice"],
            "urn": instance.urn,
            "experiments": [experiment.urn]
        }
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result)

    def test_can_filter_out_private(self):
        experiment = make_experiment()
        instance = experiment.experimentset

        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(alice, instance)
        assign_user_as_instance_viewer(bob, instance)

        serializer = ExperimentSetSerializer()
        expected = {
            "contributors": ["alice"],
            "urn": instance.urn,
            "experiments": []
        }
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result)

    def test_empty_json_object_not_found(self):
        serializer = ExperimentSetSerializer()
        expected = {}
        result = serializer.serialize(10000)
        self.assertEqual(expected, result)

    def test_empty_list_no_experiments(self):
        instance = make_experimentset()
        serializer = ExperimentSetSerializer()
        expected = []
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['experiments'])

    def test_can_serialize_queryset(self):
        instances = [
            make_experimentset(),
            make_experimentset()
        ]
        instances = ExperimentSet.objects.all()
        serializer = ExperimentSetSerializer()
        expected = {
            "experimentsets": [
                {
                    "contributors": [],
                    "urn": instances[0].urn,
                    "experiments": []
                },
                {
                    "contributors": [],
                    "urn": instances[1].urn,
                    "experiments": []
                }
            ]
        }
        result = serializer.serialize_set(instances)
        self.assertEqual(expected, result)


class TestExperimentSerializer(TestCase):

    def test_can_correctly_serialize_instance(self):
        instance = make_experiment()
        scoreset_1 = make_scoreset(experiment=instance)

        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(alice, instance)
        assign_user_as_instance_viewer(bob, instance)

        scoreset_1.publish(alice)
        serializer = ExperimentSerializer()
        expected = {
            "contributors": ["alice"],
            "experimentset": instance.experimentset.urn,
            "urn": instance.urn,
            "scoresets": [scoreset_1.urn]
        }
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result)

    def test_can_filter_out_private(self):
        instance = make_experiment()
        scoreset_1 = make_scoreset(experiment=instance)

        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(alice, instance)
        assign_user_as_instance_viewer(bob, instance)

        serializer = ExperimentSerializer()
        expected = {
            "contributors": ["alice"],
            "experimentset": instance.experimentset.urn,
            "urn": instance.urn,
            "scoresets": []
        }
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result)

    def test_empty_scoreset_list_no_scoresets(self):
        instance = make_experiment()
        serializer = ExperimentSerializer()
        expected = []
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['scoresets'])

    def test_empty_json_object_not_found(self):
        serializer = ExperimentSerializer()
        expected = {}
        result = serializer.serialize(10000)
        self.assertEqual(expected, result)

    def test_returns_correct_scoresets(self):
        instance = make_experiment()
        scoreset_1 = make_scoreset(experiment=instance)
        scoreset_2 = make_scoreset()  # not associated
        scoreset_1.publish()
        scoreset_2.publish()

        serializer = ExperimentSerializer()
        expected = [scoreset_1.urn]
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['scoresets'])

    def test_can_serialize_queryset(self):
        instances = [
            make_experiment(),
            make_experiment()
        ]
        instances = Experiment.objects.all()
        serializer = ExperimentSerializer()
        expected = {
            "experiments": [
                {
                    "contributors": [],
                    "urn": instances[0].urn,
                    "experimentset": instances[0].experimentset.urn,
                    "scoresets": []
                },
                {
                    "contributors": [],
                    "urn": instances[1].urn,
                    "experimentset": instances[1].experimentset.urn,
                    "scoresets": []
                }
            ]
        }
        result = serializer.serialize_set(instances)
        self.assertEqual(expected, result)


class TestScoreSetSerializer(TestCase):

    def test_can_serialize_minimal_example(self):
        instance = make_scoreset()
        expected = {
            "urn": instance.urn,
            "contributors": [],
            "current_version": instance.urn,
            "replaced_by": None,
            "replaces": None,
            "licence": [
                instance.licence.short_name, instance.licence.link,
            ],
            "score_columns": [],
            "count_columns": []
        }
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result)

    def test_empty_json_object_not_found(self):
        serializer = ScoreSetSerializer()
        expected = {}
        result = serializer.serialize(10000)
        self.assertEqual(expected, result)

    def test_correct_scores_columns(self):
        instance = make_scoreset()
        instance.dataset_columns = {
            constants.score_columns: ["hgvs", "score"], 
            constants.count_columns: []
        }
        instance.save()
        expected = ["hgvs", "score"]
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result["score_columns"])

    def test_correct_counts_columns(self):
        instance = make_scoreset()
        instance.dataset_columns = {
            constants.score_columns: [], 
            constants.count_columns: ["hgvs", "counts"]
        }
        instance.save()
        expected = ["hgvs", "counts"]
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result["count_columns"])

    def test_current_version_traverses_and_links_to_newest(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset(instance_1.experiment, instance_1)
        instance_3 = make_scoreset(instance_2.experiment, instance_2)

        expected = instance_3.urn
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance_1.pk)
        self.assertEqual(expected, result['current_version'])

    def test_value_is_null_when_no_next_version(self):
        instance = make_scoreset()
        expected = None
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['replaced_by'])

    def test_correct_replaced_by(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset(instance_1.experiment, instance_1)
        expected = instance_2.urn
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance_1.pk)
        self.assertEqual(expected, result['replaced_by'])

    def test_value_is_null_when_no_previous_version(self):
        instance = make_scoreset()
        serializer = ScoreSetSerializer()
        expected = None
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['replaces'])

    def test_replaces_is_none_when_no_it_does_not_replace_any_instance(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset(instance_1.experiment, instance_1)

        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance_2.pk)
        self.assertEqual(instance_1.urn, result['replaces'])


class TestUserSerializer(TestCase):

    def setUp(self):
        self.alice = User.objects.create(username="alice", first_name="Alice")
        self.bob = User.objects.create(username="bob")

    def test_can_serialize_minimal_example(self):
        exps = make_experimentset()
        exp = make_experiment(exps)
        scs = make_scoreset(exp)

        assign_user_as_instance_admin(self.alice, exps)
        assign_user_as_instance_admin(self.alice, exp)
        assign_user_as_instance_admin(self.alice, scs)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, filter_private=False)
        expected = {
            "username": "alice",
            "first_name": "Alice",
            "last_name": "",
            "experimentsets": [exps.urn],
            "experiments": [exp.urn],
            "scoresets": [scs.urn],
        }
        self.assertEqual(expected, result)

    def test_empty_json_object_not_found(self):
        serializer = UserSerializer()
        expected = {}
        result = serializer.serialize(10000)
        self.assertEqual(expected, result)

    def test_can_filter_out_private_exps_admin_instances(self):
        instance_1 = make_experimentset()
        instance_2 = make_experimentset()
        instance_2.publish()

        assign_user_as_instance_admin(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk)
        expected = [instance_2.urn]
        self.assertEqual(expected, result["experimentsets"])

    def test_can_filter_out_private_exp_admin_instances(self):
        instance_1 = make_experiment()
        instance_2 = make_experiment()
        instance_2.publish()

        assign_user_as_instance_admin(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk)
        expected = [instance_2.urn]
        self.assertEqual(expected, result["experiments"])

    def test_can_filter_out_private_scs_admin_instances(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset()
        instance_2.publish()

        assign_user_as_instance_admin(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk)
        expected = [instance_2.urn]
        self.assertEqual(expected, result["scoresets"])

    def test_only_show_admin_experimentsets(self):
        instance_1 = make_experimentset()
        instance_2 = make_experimentset()

        assign_user_as_instance_viewer(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, False)
        expected = [instance_2.urn]
        self.assertEqual(expected, result["experimentsets"])

    def test_only_show_admin_experiments(self):
        instance_1 = make_experiment()
        instance_2 = make_experiment()

        assign_user_as_instance_viewer(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, False)
        expected = [instance_2.urn]
        self.assertEqual(expected, result["experiments"])

    def test_only_show_admin_scoresets(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset()

        assign_user_as_instance_viewer(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, False)
        expected = [instance_2.urn]
        self.assertEqual(expected, result["scoresets"])
