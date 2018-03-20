from django.test import TestCase
from django.contrib.auth import get_user_model

from main.models import Licence
from accounts.permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer
)
from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet, SCORES_KEY, COUNTS_KEY

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
    scs.licence_type = Licence.get_default()
    scs.save()
    return scs


class TestExperimentSetSerializer(TestCase):

    def test_can_correctly_serialize_instance(self):
        experiment = make_experiment()
        experiment.publish()
        instance = experiment.experimentset
        instance.publish()
        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(alice, instance)
        assign_user_as_instance_viewer(bob, instance)

        serializer = ExperimentSetSerializer()
        expected = {
            "authors": ["alice"],
            "urn": instance.accession,
            "experiments": [experiment.accession]
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
            "authors": ["alice"],
            "urn": instance.accession,
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
                    "authors": [],
                    "urn": instances[0].accession,
                    "experiments": []
                },
                {
                    "authors": [],
                    "urn": instances[1].accession,
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
        scoreset_1.publish()

        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        assign_user_as_instance_admin(alice, instance)
        assign_user_as_instance_viewer(bob, instance)

        serializer = ExperimentSerializer()
        expected = {
            "authors": ["alice"],
            "experimentset": instance.experimentset.accession,
            "urn": instance.accession,
            "scoresets": [scoreset_1.accession]
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
            "authors": ["alice"],
            "experimentset": instance.experimentset.accession,
            "urn": instance.accession,
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
        expected = [scoreset_1.accession]
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
                    "authors": [],
                    "urn": instances[0].accession,
                    "experimentset": instances[0].experimentset.accession,
                    "scoresets": []
                },
                {
                    "authors": [],
                    "urn": instances[1].accession,
                    "experimentset": instances[1].experimentset.accession,
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
            "urn": instance.accession,
            "authors": [],
            "current_version": instance.accession,
            "replaced_by": '',
            "replaces": '',
            "licence": [
                instance.licence_type.short_name, instance.licence_type.link,
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
            SCORES_KEY: ["hgvs", "score"], COUNTS_KEY: []
        }
        instance.save()
        expected = ["hgvs", "score"]
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result["score_columns"])

    def test_correct_counts_columns(self):
        instance = make_scoreset()
        instance.dataset_columns = {
            SCORES_KEY: [], COUNTS_KEY: ["hgvs", "counts"]
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

        expected = instance_3.accession
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance_1.pk)
        self.assertEqual(expected, result['current_version'])

    def test_empty_string_no_replaced_by(self):
        instance = make_scoreset()
        expected = ''
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['replaced_by'])

    def test_correct_replaced_by(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset(instance_1.experiment, instance_1)
        expected = instance_2.accession
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance_1.pk)
        self.assertEqual(expected, result['replaced_by'])

    def test_empty_string_no_replaces(self):
        instance = make_scoreset()
        serializer = ScoreSetSerializer()
        expected = ''
        result = serializer.serialize(instance.pk)
        self.assertEqual(expected, result['replaces'])

    def test_correct_replaces(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset(instance_1.experiment, instance_1)

        expected = instance_1.accession
        serializer = ScoreSetSerializer()
        result = serializer.serialize(instance_2.pk)
        self.assertEqual(expected, result['replaces'])


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
            "experimentsets": [exps.accession],
            "experiments": [exp.accession],
            "scoresets": [scs.accession],
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
        expected = [instance_2.accession]
        self.assertEqual(expected, result["experimentsets"])

    def test_can_filter_out_private_exp_admin_instances(self):
        instance_1 = make_experiment()
        instance_2 = make_experiment()
        instance_2.publish()

        assign_user_as_instance_admin(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk)
        expected = [instance_2.accession]
        self.assertEqual(expected, result["experiments"])

    def test_can_filter_out_private_scs_admin_instances(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset()
        instance_2.publish()

        assign_user_as_instance_admin(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk)
        expected = [instance_2.accession]
        self.assertEqual(expected, result["scoresets"])

    def test_only_show_admin_experimentsets(self):
        instance_1 = make_experimentset()
        instance_2 = make_experimentset()

        assign_user_as_instance_viewer(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, False)
        expected = [instance_2.accession]
        self.assertEqual(expected, result["experimentsets"])

    def test_only_show_admin_experiments(self):
        instance_1 = make_experiment()
        instance_2 = make_experiment()

        assign_user_as_instance_viewer(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, False)
        expected = [instance_2.accession]
        self.assertEqual(expected, result["experiments"])

    def test_only_show_admin_scoresets(self):
        instance_1 = make_scoreset()
        instance_2 = make_scoreset()

        assign_user_as_instance_viewer(self.alice, instance_1)
        assign_user_as_instance_admin(self.alice, instance_2)

        serializer = UserSerializer()
        result = serializer.serialize(self.alice.pk, False)
        expected = [instance_2.accession]
        self.assertEqual(expected, result["scoresets"])
