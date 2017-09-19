import json

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

from accounts.permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer
)
from experiment.models import Experiment, ExperimentSet
from scoreset.models import ScoreSet, Variant, SCORES_KEY, COUNTS_KEY


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
    return ScoreSet.objects.create(experiment=experiment, replaces=replaces)


class TestUserAPIViews(TestCase):

    def setUp(self):
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_can_serialize_all_users(self):
        response = self.client.get("/api/get/user/all/")
        result = json.loads(response.content.decode('utf-8'))
        expected = {
            "users": [
                {
                    "username": "alice",
                    "first_name": "",
                    "last_name": "",
                    'experimentsets': [],
                    'experiments': [],
                    'scoresets': []
                },
                {
                    "username": "bob",
                    "first_name": "",
                    "last_name": "",
                    'experimentsets': [],
                    'experiments': [],
                    'scoresets': []
                }
            ]
        }
        self.assertEqual(expected, result)

    def test_filters_out_private_entries(self):
        scs_1 = make_scoreset()
        scs_2 = make_scoreset()
        assign_user_as_instance_admin(self.alice, scs_1)
        assign_user_as_instance_admin(self.alice, scs_2)
        scs_2.publish()

        response = self.client.get("/api/get/user/alice/")
        result = json.loads(response.content.decode('utf-8'))
        expected = {
            "username": "alice",
            "first_name": "",
            "last_name": "",
            'experimentsets': [],
            'experiments': [],
            'scoresets': [scs_2.accession]
        }
        self.assertEqual(expected, result)

    def test_404_cannot_find_username(self):
        response = self.client.get("/api/get/user/dddd/")
        self.assertEqual(response.status_code, 404)


class TestExperimentSetAPIViews(TestCase):

    def test_filters_out_private(self):
        exps = make_experimentset()
        response = self.client.get("/api/get/experimentset/all/")
        result = json.loads(response.content.decode('utf-8'))
        expected = {"experimentsets": []}
        self.assertEqual(expected, result)

    def test_404_private_experimentset(self):
        exps = make_experimentset()
        response = self.client.get(
            "/api/get/experimentset/{}/".format(exps.accession)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/get/experimentset/dddd/")
        self.assertEqual(response.status_code, 404)


class TestExperimentAPIViews(TestCase):

    def test_filters_out_private(self):
        instance = make_experiment()
        response = self.client.get("/api/get/experiment/all/")
        result = json.loads(response.content.decode('utf-8'))
        expected = {"experiments": []}
        self.assertEqual(expected, result)

    def test_404_private(self):
        instance = make_experiment()
        response = self.client.get(
            "/api/get/experimentset/{}/".format(instance.accession)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_not_found(self):
        response = self.client.get("/api/get/experiment/dddd/")
        self.assertEqual(response.status_code, 404)


class TestScoreSetAPIViews(TestCase):

    def test_filters_out_private(self):
        instance = make_scoreset()
        response = self.client.get("/api/get/scoreset/all/")
        result = json.loads(response.content.decode('utf-8'))
        expected = {"scoresets": []}
        self.assertEqual(expected, result)

    def test_404_private(self):
        instance = make_scoreset()
        response = self.client.get(
            "/api/get/scoreset/{}/".format(instance.accession)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_private_download_scores(self):
        instance = make_scoreset()
        response = self.client.get(
            "/api/get/scoreset/{}/scores/".format(instance.accession)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_private_download_counts(self):
        instance = make_scoreset()
        response = self.client.get(
            "/api/get/scoreset/{}/counts/".format(instance.accession)
        )
        self.assertEqual(response.status_code, 404)

    def test_empty_text_response_download_counts_but_has_no_counts(self):
        instance = make_scoreset()
        instance.publish()
        response = self.client.get(
            "/api/get/scoreset/{}/counts/".format(instance.accession)
        )
        self.assertEqual(list(response.streaming_content), [])

    def test_404_not_found(self):
        response = self.client.get("/api/get/scoreset/dddd/")
        self.assertEqual(response.status_code, 404)

    def test_can_download_scores(self):
        scs = make_scoreset()
        scs.publish()
        scs.dataset_columns = {
            SCORES_KEY: ["hgvs", "score"],
            COUNTS_KEY: ["hgvs", "count"]
        }
        scs.save()
        var = Variant.objects.create(
            scoreset=scs, hgvs="test",
            data={
                SCORES_KEY: {"hgvs": "test", "score": "1"},
                COUNTS_KEY: {"hgvs": "test", "count": "1"}
            }
        )
        response = self.client.get(
            "/api/get/scoreset/{}/scores/".format(scs.accession)
        )
        self.assertEqual(
            list(response.streaming_content),
            [b'hgvs,score\n', b'test,1\n']
        )

    def test_can_download_counts(self):
        scs = make_scoreset()
        scs.publish()
        scs.dataset_columns = {
            SCORES_KEY: ["hgvs", "score"],
            COUNTS_KEY: ["hgvs", "count"]
        }
        scs.save()
        var = Variant.objects.create(
            scoreset=scs, hgvs="test",
            data={
                SCORES_KEY: {"hgvs": "test", "score": "1"},
                COUNTS_KEY: {"hgvs": "test", "count": "1"}
            }
        )
        response = self.client.get(
            "/api/get/scoreset/{}/counts/".format(scs.accession)
        )
        self.assertEqual(
            list(response.streaming_content),
            [b'hgvs,count\n', b'test,1\n']
        )
