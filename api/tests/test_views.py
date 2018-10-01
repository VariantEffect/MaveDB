import io
import json
import csv

from django.test import TestCase
from django.contrib.auth import get_user_model

import dataset.constants as constants
from dataset.utilities import publish_dataset
from dataset.models import scoreset
from dataset.factories import (
    ScoreSetFactory, ExperimentFactory, ExperimentSetFactory
)

from variant.factories import dna_hgvs, protein_hgvs
from variant.models import Variant

User = get_user_model()


class TestDatasetListViewSet(TestCase):
    def test_authenticate_user_not_none_if_token_valid(self):
        pass

    def test_authenticate_user_none_if_no_profiles_found(self):
        pass

    def test_authenticate_user_none_if_no_token(self):
        pass

    def test_dispatch_sets_token_if_supplied(self):
        pass

    def test_list_includes_private_for_valid_user(self):
        pass

    def test_list_excludes_private_no_user(self):
        pass

    def test_list_error_no_user_but_token_supplied(self):
        pass

    def test_retreive_missing_token_no_token(self):
        pass

    def test_retreive_private_missing_token(self):
        pass

    def test_retreive_private_invalid_token_error(self):
        pass


class TestExperimentSetAPIViews(TestCase):

    def test_filters_out_private(self):
        exps = ExperimentSetFactory(private=True)
        response = self.client.get("/api/experimentsets/")
        result = json.loads(response.content.decode('utf-8'))
        expected = []
        self.assertEqual(expected, result)
        
    def test_shows_public(self):
        instance = ExperimentSetFactory()
        instance.private = False
        instance.save()
        response = self.client.get("/api/experimentsets/")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result), 1)

    def test_404_private_experimentset(self):
        exps = ExperimentSetFactory()
        response = self.client.get(
            "/api/experimentsets/{}/".format(exps.urn)
        )
        self.assertEqual(response.status_code, 404)
        
    def test_404_wrong_address(self):
        instance = ExperimentSetFactory()
        response = self.client.get(
            "/api/experimentset/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/experimentsets/dddd/")
        self.assertEqual(response.status_code, 404)
        
    def test_search_works(self):
        instance1 = ExperimentSetFactory()
        instance2 = ExperimentSetFactory()
        instance1.private = False
        instance2.private = False
        instance1.save()
        instance2.save()
        response = self.client.get(
            "/api/experimentsets/?title={}".format(instance1.title)
        )
        self.assertContains(response, instance1.urn)
        self.assertNotContains(response, instance2.urn)
        

class TestExperimentAPIViews(TestCase):

    def test_filters_out_private(self):
        instance = ExperimentFactory()
        response = self.client.get("/api/experiments/")
        result = json.loads(response.content.decode('utf-8'))
        expected = []
        self.assertEqual(expected, result)
        
    def test_shows_public(self):
        instance = ExperimentFactory()
        instance.private = False
        instance.save()
        response = self.client.get("/api/experiments/")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result), 1)

    def test_404_private(self):
        instance = ExperimentFactory()
        response = self.client.get(
            "/api/experiments/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)
        
    def test_404_wrong_address(self):
        instance = ExperimentFactory()
        response = self.client.get(
            "/api/experiment/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_not_found(self):
        response = self.client.get("/api/experiments/dddd/")
        self.assertEqual(response.status_code, 404)
        
    def test_search_works(self):
        instance1 = ExperimentFactory()
        instance2 = ExperimentFactory()
        instance1.private = False
        instance2.private = False
        instance1.save()
        instance2.save()
        response = self.client.get(
            "/api/experiments/?title={}".format(instance1.title)
        )
        self.assertContains(response, instance1.urn)
        self.assertNotContains(response, instance2.urn)


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
        
    def test_shows_public(self):
        instance = ScoreSetFactory()
        instance.private = False
        instance.save()
        response = self.client.get("/api/scoresets/")
        result = json.loads(response.content.decode('utf-8'))
        self.assertEqual(len(result), 1)

    def test_404_private(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoreset/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)
        
    def test_404_wrong_address(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoreset/{}/".format(instance.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_private_download_scores(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoresets/{}/scores/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 404)

    def test_404_private_download_counts(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoresets/{}/counts/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 404)

    def test_404_private_download_meta(self):
        instance = ScoreSetFactory()
        response = self.client.get(
            "/api/scoresets/{}/metadata/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 404)

    def test_404_not_found(self):
        response = self.client.get("/api/scoresets/dddd/")
        self.assertEqual(response.status_code, 404)
        
    def test_search_works(self):
        instance1 = ScoreSetFactory()
        instance2 = ScoreSetFactory()
        instance1.private = False
        instance2.private = False
        instance1.save()
        instance2.save()
        response = self.client.get(
            "/api/scoresets/?title={}".format(instance1.title)
        )
        self.assertContains(response, instance1.urn)
        self.assertNotContains(response, instance2.urn)

    def test_can_download_scores(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save()
        variant = Variant.objects.create(
            hgvs_nt=dna_hgvs[0], hgvs_pro=protein_hgvs[0],
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "1"}
            }
        )
        
        response = self.client.get("/api/scoresets/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        
        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'score']
        data = [variant.hgvs_nt, variant.hgvs_pro, '1']
        self.assertEqual(rows, [header, data])
        
    def test_comma_in_value_enclosed_by_quotes(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count,count"]
        }
        scs.save(save_parents=True)
        variant = Variant.objects.create(
            hgvs_nt=dna_hgvs[0], hgvs_pro=protein_hgvs[0],
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count,count": "4"}
            }
        )
        response = self.client.get("/api/scoresets/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))

        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'count,count']
        data = [variant.hgvs_nt, variant.hgvs_pro, '4']
        self.assertEqual(rows, [header, data])

    def test_can_download_counts(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        variant = Variant.objects.create(
            hgvs_nt=dna_hgvs[0], hgvs_pro=protein_hgvs[0],
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoresets/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        
        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'count']
        data = [variant.hgvs_nt, variant.hgvs_pro, '4']
        self.assertEqual(rows, [header, data])
        
    def test_none_hgvs_written_as_blank(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        variant = Variant.objects.create(
            hgvs_nt=dna_hgvs[0], hgvs_pro=None,
            scoreset=scs,
            data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoresets/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
    
        header = [constants.hgvs_nt_column, constants.hgvs_pro_column, 'score']
        data = [variant.hgvs_nt, '', '1']
        self.assertEqual(rows, [header, data])
        
    def test_no_variants_empty_file(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: ["count"]
        }
        scs.save(save_parents=True)
        scs.children.delete()
        
        response = self.client.get("/api/scoresets/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])
        
        response = self.client.get("/api/scoresets/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])

    def test_empty_scores_returns_empty_file(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: [],
            constants.count_columns: ['count']
        }
        scs.save(save_parents=True)
        _ = Variant.objects.create(
            hgvs_nt=dna_hgvs[0], hgvs_pro=protein_hgvs[0],
            scoreset=scs, data={
                constants.variant_score_data: {},
                constants.variant_count_data: {"count": "4"}
            }
        )
        response = self.client.get("/api/scoresets/{}/scores/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])
        
    def test_empty_counts_returns_empty_file(self):
        scs = ScoreSetFactory()
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        scs.dataset_columns = {
            constants.score_columns: ["score"],
            constants.count_columns: []
        }
        scs.save(save_parents=True)
        _ = Variant.objects.create(
            hgvs_nt=dna_hgvs[0], hgvs_pro=protein_hgvs[0],
            scoreset=scs, data={
                constants.variant_score_data: {"score": "1"},
                constants.variant_count_data: {}
            }
        )
        response = self.client.get("/api/scoresets/{}/counts/".format(scs.urn))
        rows = list(
            csv.reader(
                io.TextIOWrapper(
                    io.BytesIO(response.content), encoding='utf-8')))
        self.assertEqual(rows, [])

    def test_can_download_metadata(self):
        scs = ScoreSetFactory(private=False)
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        response = json.loads(self.client.get(
            "/api/scoresets/{}/metadata/".format(scs.urn)
        ).content.decode())
        self.assertEqual(response, scs.extra_metadata)
