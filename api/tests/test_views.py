import io
import json
import csv
from datetime import timedelta

from django.test import TestCase, RequestFactory, mock
from django.contrib.auth import get_user_model

from rest_framework import exceptions

from accounts.factories import UserFactory

import dataset.constants as constants
from dataset.utilities import publish_dataset
from dataset.models import scoreset, experimentset
from dataset.factories import (
    ScoreSetFactory, ExperimentFactory, ExperimentSetFactory
)

from variant.factories import dna_hgvs, protein_hgvs
from variant.models import Variant

from .. import views


User = get_user_model()


class TestAuthenticate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.client.login(
            username=self.user.username, password=self.user.password)
        
    def test_returns_request_user_if_token_is_none(self):
        request = self.factory.get('/', HTTP_AUTHORIZATION=None)
        request.user = self.user
        user, token = views.authenticate(request)
        self.assertIs(self.user, user)
        self.assertIsNone(token)
        
    def test_raises_auth_failed_invalid_token_format(self):
        with self.assertRaises(exceptions.AuthenticationFailed):
            request = self.factory.get('/', HTTP_AUTHORIZATION='a')
            views.authenticate(request)
            
    def test_raises_auth_failed_invalid_token_for_user(self):
        token, exp = self.user.profile.generate_token()
        self.user.profile.generate_token()
        with self.assertRaises(exceptions.AuthenticationFailed):
            request = self.factory.get('/', HTTP_AUTHORIZATION=token)
            views.authenticate(request)
            
    def test_raises_auth_failed_expired_token(self):
        token, _ = self.user.profile.generate_token()
        profile = self.user.profile
        profile.auth_token_expiry -= timedelta(days=100)
        profile.save()
        with self.assertRaises(exceptions.AuthenticationFailed):
            request = self.factory.get('/', HTTP_AUTHORIZATION=token)
            views.authenticate(request)
            
    def test_returns_user_and_token_on_success(self):
        token, _ = self.user.profile.generate_token()
        request = self.factory.get('/', HTTP_AUTHORIZATION=token)
        user, ret_token = views.authenticate(request)
        self.assertEqual(token, ret_token)
        self.assertEqual(self.user, user)
        
    def test_returns_none_none_by_default(self):
        request = self.factory.get('/', HTTP_AUTHORIZATION=None)
        request.user = None
        user, ret_token = views.authenticate(request)
        self.assertIsNone(ret_token)
        self.assertIsNone(user)
        

class TestCheckPermission(TestCase):
    def test_raises_403_error_private_and_user_is_none(self):
        with self.assertRaises(exceptions.PermissionDenied):
            instance = ScoreSetFactory(private=True)
            views.check_permission(instance, user=None)
            
    def test_raises_403_private_instance_user_not_a_contributor(self):
        with self.assertRaises(exceptions.PermissionDenied):
            instance = ScoreSetFactory(private=True)
            user = UserFactory()
            views.check_permission(instance, user=user)
            
    def test_returns_instance_when_private_and_user_is_contributor(self):
        instance = ScoreSetFactory(private=True)
        user = UserFactory()
        instance.add_viewers(user)
        self.assertIs(instance, views.check_permission(instance, user=user))
        
    def test_returns_instance_when_it_is_public(self):
        instance = ScoreSetFactory(private=False)
        self.assertIs(instance, views.check_permission(instance, user=None))
        

class TestAuthenticatedViewSet(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @mock.patch('api.views.authenticate',
                side_effect=lambda request: (None, None))
    def test_dispatch_calls_authenticate(self, patch):
        self.client.get('/api/experimentsets/')
        patch.assert_called()

    @mock.patch.object(views.AuthenticatedViewSet, 'auth_token', return_value=None)
    @mock.patch.object(views.AuthenticatedViewSet, 'user', return_value=None)
    @mock.patch.object(views.AuthenticatedViewSet, 'get_serializer_context', return_value=dict())
    def test_get_context_adds_in_user_and_auth_token(self, p1, p2, p3):
        self.client.get('/api/experimentsets/')
        p1.assert_called()
        self.assertIsNone(p2.return_value)
        self.assertIsNone(p3.return_value)
        

class TestDatasetListViewSet(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserFactory()
        self.client.login(
            username=self.user.username, password=self.user.password)
    
    @mock.patch('dataset.models.base.DatasetModel.viewable_instances_for_user',
                side_effect=lambda user: experimentset.ExperimentSet.objects.none())
    def test_get_qs_calls_viewable_instances_for_user_with_authed_user(self, patch):
        request = self.factory.get(
            '/api/experimentsets/',
            HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({'get': 'list'})(request)
        patch.assert_called_with(*(self.user,))
        
    @mock.patch('api.views.check_permission', side_effect=lambda instance, user: instance)
    def test_get_object_calls_check_perm_with_instance_and_user(self, patch):
        i = ExperimentSetFactory(private=False)
        request = self.factory.get(
            '/api/experimentsets/{}/'.format(i.urn),
            HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({'get': 'retrieve'})(request, urn=i.urn)
        patch.assert_called_with(*(i, self.user,))
        
    @mock.patch('api.views.check_permission')
    def test_get_object_doesnt_call_check_perm_instance_not_found(self, patch):
        request = self.factory.get(
            '/api/experimentsets/{}/'.format('aaa'),
            HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({'get': 'retrieve'})(request, urn='aaa')
        patch.assert_not_called()

    @mock.patch('api.views.check_permission')
    def test_get_object_doesnt_call_check_perm_urn_is_none(self, patch):
        request = self.factory.get(
            '/api/experimentsets/{}/'.format('aaa'),
            HTTP_AUTHORIZATION=None
        )
        request.user = self.user
        views.ExperimentSetViewset.as_view({'get': 'retrieve'})(request, urn=None)
        patch.assert_not_called()


class TestExperimentSetAPIViews(TestCase):
    factory = ExperimentSetFactory
    url = 'experimentsets'
    
    def test_403_private_experimentset(self):
        inst = self.factory(private=True)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn)
        )
        self.assertEqual(response.status_code, 403)
    
    def test_OK_private_experimentset_when_authenticated(self):
        inst = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        inst.add_viewers(user)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertEqual(response.status_code, 200)
    
    def test_404_wrong_address(self):
        inst = self.factory()
        response = self.client.get(
            "/api/{}/{}/".format(self.url + 'aaa', inst.urn)
        )
        self.assertEqual(response.status_code, 404)
    
    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/{}/dddd/".format(self.url))
        self.assertEqual(response.status_code, 404)
    
    def test_list_excludes_private_when_not_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        response = self.client.get("/api/{}/".format(self.url))
        self.assertNotContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)
    
    def test_list_includes_private_when_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        user = UserFactory()
        user.profile.generate_token()
        instance1.add_viewers(user)
        response = self.client.get(
            "/api/{}/".format(self.url),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)
        

class TestExperimentAPIViews(TestCase):
    factory = ExperimentFactory
    url = 'experiments'
    
    def test_403_private_experimentset(self):
        inst = self.factory(private=True)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn)
        )
        self.assertEqual(response.status_code, 403)
    
    def test_OK_private_experimentset_when_authenticated(self):
        inst = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        inst.add_viewers(user)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertEqual(response.status_code, 200)
    
    def test_404_wrong_address(self):
        inst = self.factory()
        response = self.client.get(
            "/api/{}/{}/".format(self.url + 'aaa', inst.urn)
        )
        self.assertEqual(response.status_code, 404)
    
    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/{}/dddd/".format(self.url))
        self.assertEqual(response.status_code, 404)
    
    def test_list_excludes_private_when_not_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        response = self.client.get("/api/{}/".format(self.url))
        self.assertNotContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)
    
    def test_list_includes_private_when_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        user = UserFactory()
        user.profile.generate_token()
        instance1.add_viewers(user)
        response = self.client.get(
            "/api/{}/".format(self.url),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)


class TestScoreSetAPIViews(TestCase):
    factory = ScoreSetFactory
    url = 'scoresets'
    
    def setUp(self):
        Variant.objects.all().delete()
        scoreset.ScoreSet.objects.all().delete()
    
    def tearDown(self):
        Variant.objects.all().delete()
        scoreset.ScoreSet.objects.all().delete()
    
    # ---- DRF Views
    def test_403_private_experimentset(self):
        inst = self.factory(private=True)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn)
        )
        self.assertEqual(response.status_code, 403)

    def test_OK_private_experimentset_when_authenticated(self):
        inst = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        inst.add_viewers(user)
        response = self.client.get(
            "/api/{}/{}/".format(self.url, inst.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertEqual(response.status_code, 200)

    def test_404_wrong_address(self):
        inst = self.factory()
        response = self.client.get(
            "/api/{}/{}/".format(self.url + 'aaa', inst.urn)
        )
        self.assertEqual(response.status_code, 404)

    def test_404_experimentset_not_found(self):
        response = self.client.get("/api/{}/dddd/".format(self.url))
        self.assertEqual(response.status_code, 404)

    def test_list_excludes_private_when_not_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        response = self.client.get("/api/{}/".format(self.url))
        self.assertNotContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)

    def test_list_includes_private_when_authenticated(self):
        instance1 = self.factory(private=True)
        instance2 = self.factory(private=False)
        user = UserFactory()
        user.profile.generate_token()
        instance1.add_viewers(user)
        response = self.client.get(
            "/api/{}/".format(self.url),
            HTTP_AUTHORIZATION=user.profile.auth_token,
        )
        self.assertContains(response, instance1.urn)
        self.assertContains(response, instance2.urn)
    
    # ----- Function based file download views
    def test_403_private_download_scores(self):
        instance = self.factory(private=True)
        response = self.client.get(
            "/api/scoresets/{}/scores/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 403)

    def test_403_private_download_counts(self):
        instance = self.factory(private=True)
        response = self.client.get(
            "/api/scoresets/{}/counts/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 403)

    def test_403_private_download_meta(self):
        instance = self.factory(private=True)
        response = self.client.get(
            "/api/scoresets/{}/metadata/".format(instance.urn)
        )
        self.assertTrue(response.status_code, 403)
        
    def test_OK_private_download_scores_when_authenticated(self):
        instance = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        instance.add_viewers(user)
        response = self.client.get(
            "/api/scoresets/{}/scores/".format(instance.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token
        )
        self.assertTrue(response.status_code, 200)

    def test_OK_private_download_counts_when_authenticated(self):
        instance = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        instance.add_viewers(user)
        response = self.client.get(
            "/api/scoresets/{}/counts/".format(instance.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token
        )
        self.assertTrue(response.status_code, 200)

    def test_OK_private_download_meta_when_authenticated(self):
        instance = self.factory(private=True)
        user = UserFactory()
        user.profile.generate_token()
        instance.add_viewers(user)
        response = self.client.get(
            "/api/scoresets/{}/metadata/".format(instance.urn),
            HTTP_AUTHORIZATION=user.profile.auth_token
        )
        self.assertTrue(response.status_code, 200)

    def test_404_not_found(self):
        response = self.client.get("/api/scoresets/dddd/")
        self.assertEqual(response.status_code, 404)
        
    def test_can_download_scores(self):
        scs = self.factory()
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
        scs = self.factory()
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
        scs = self.factory()
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
        scs = self.factory()
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
        scs = self.factory()
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
        scs = self.factory()
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
        scs = self.factory()
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
        scs = self.factory(private=False)
        scs = publish_dataset(scs)
        scs.refresh_from_db()
        response = json.loads(self.client.get(
            "/api/scoresets/{}/metadata/".format(scs.urn)
        ).content.decode())
        self.assertEqual(response, scs.extra_metadata)
