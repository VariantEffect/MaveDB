import io
import json
import csv

from django.test import TestCase
from django.contrib.auth import get_user_model

import dataset.constants as constants
from dataset.models import scoreset
from dataset.factories import (
    ScoreSetFactory, ExperimentFactory, ExperimentSetFactory
)

from variant.factories import VariantFactory
from variant.models import Variant

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
    
    def setUp(self):
        Variant.objects.all().delete()
        scoreset.ScoreSet.objects.all().delete()
    
    def tearDown(self):
        Variant.objects.all().delete()
        scoreset.ScoreSet.objects.all().delete()

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
        
    def test_404_wrong_address(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/blahblah/{}/".format(instance.urn)
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
        variant = VariantFactory(
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "1"}
            }
        )
        response = self.client.get("/api/scoreset/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        
        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'score']
        data = [variant.hgvs_nt, variant.hgvs_pro, '1']
        self.assertEqual(rows, [header, data])
        
    def test_comma_in_value_enclosed_by_quotes(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count,count"]
        }
        scs.save(save_parents=True)
        variant = VariantFactory(
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count,count": "4"}
            }
        )
        response = self.client.get("/api/scoreset/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))

        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'count,count']
        data = [variant.hgvs_nt, variant.hgvs_pro, '4']
        self.assertEqual(rows, [header, data])

    def test_can_download_counts(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        variant = VariantFactory(
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoreset/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        
        
        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'count']
        data = [variant.hgvs_nt, variant.hgvs_pro, '4']
        self.assertEqual(rows, [header, data])
        
    def test_none_hgvs_written_as_blank(self):
        scs = ScoreSetFactory()
        scs.publish()
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        variant = VariantFactory(
            scoreset=scs, hgvs_pro=None,
            data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoreset/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
    
        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'score']
        data = [variant.hgvs_nt, '', '1']
        self.assertEqual(rows, [header, data])
        
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
            scoreset=scs, hgvs_nt="1A>G",
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
            scoreset=scs, data={
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
