import io
import json
import csv

from django.test import TestCase
from django.contrib.auth import get_user_model

import dataset.constants as constants
from dataset.factories import (
    ScoreSetFactory, ExperimentFactory, ExperimentSetFactory
)

from variant.factories import VariantFactory

User = get_user_model()


class TestExperimentSetAPIViews(TestCase):

    def test_filters_out_private(self):
        exps = ExperimentSetFactory(private=True)
        response = self.client.get("/api/experimentsets/")
        result = json.loads(response.content.decode('utf-8'))
        expected = []
        self.assertEqual(expected, result)

    def test_404_private_experimentset(self):
        exps = ExperimentSetFactory()
        response = self.client.get(
            "/api/experimentset/{}/".format(exps.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/experimentset/dddd/")
        self.assertEqual(response.status_code, 404)


class TestExperimentAPIViews(TestCase):

    def test_filters_out_private(self):
        instance = ExperimentFactory()
        response = self.client.get("/api/experiments/")
        result = json.loads(response.content.decode('utf-8'))
        expected = []
        self.assertEqual(expected, result)

    def test_404_private(self):
        instance = ExperimentFactory()
        response = self.client.get(
            "/api/experimentset/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_not_found(self):
        response = self.client.get("/api/experiment/dddd/")
        self.assertEqual(response.status_code, 404)


class TestScoreSetAPIViews(TestCase):

    def test_filters_out_private(self):
        instance = ScoreSetFactory()
        response = self.client.get("/api/scoresets/")
        result = json.loads(response.content.decode('utf-8'))
        expected = []
        self.assertEqual(expected, result)

    def test_404_private(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoreset/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_private_download_scores(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoreset/{}/scores/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 404)

    def test_404_private_download_counts(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoreset/{}/counts/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 404)

    def test_404_private_download_meta(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoreset/{}/metadata/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 404)

    def test_404_not_found(self):
        response = self.client.get("/api/scoreset/dddd/")
        self.assertEqual(response.status_code, 404)

    def test_can_download_scores(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save()
        _ = VariantFactory(
            scoreset=scs, hgvs="test",
            data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "1"}
            }
        )
        response = self.client.get("/api/scoreset/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [['hgvs', 'score'], ['test', '1']])

    def test_can_download_counts(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        _ = VariantFactory(
            scoreset=scs, hgvs="test",
            data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoreset/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [['hgvs', 'count'], ['test', '4']])
    
    def test_no_variants_empty_file(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        response = self.client.get("/api/scoreset/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])
        
        response = self.client.get("/api/scoreset/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])

    def test_empty_scores_returns_empty_file(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: [],
            constants.count_columns: ['count']
        }
        scs.save(save_parents=True)
        _ = VariantFactory(
            scoreset=scs, hgvs="test",
            data={
                constants.variant_score_data: {},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoreset/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])
        
    def test_empty_counts_returns_empty_file(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: []
        }
        scs.save(save_parents=True)
        _ = VariantFactory(
            scoreset=scs, hgvs="test",
            data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {}
            }
        )
        response = self.client.get("/api/scoreset/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])

    def test_can_download_metadata(self):
        scs = ScoreSetFactory(private=False)
        scs.publish()
        scs.refresh_from_db()
        response = json.loads(self.client.get(
            "/api/scoreset/{}/metadata/".format(scs.urn)
        ).content.decode())
        self.assertEqual(response, scs.extra_metadata)
