
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase, TransactionTestCase, RequestFactory

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login

from guardian.shortcuts import assign_perm, remove_perm

from accounts.models import user_is_admin_for_instance, PermissionTypes

from main.models import Keyword

from experiment.models import Experiment

from scoreset.models import ScoreSet, Variant
from scoreset.views import (
    ScoresetDetailView, scoreset_create_view,
    download_scoreset_data, download_scoreset_metadata
)


class TestScoreSetSetDetailView(TestCase):
    """
    Test that experimentsets are displayed correctly to the public.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.User = get_user_model()
        self.factory = RequestFactory()
        self.exp = Experiment.objects.create(target="test", wt_sequence="AT")

    def test_uses_correct_template(self):
        obj = ScoreSet.objects.create(experiment=self.exp, private=False)
        response = self.client.get('/scoreset/{}/'.format(obj.accession))
        self.assertTemplateUsed(response, 'scoreset/scoreset.html')

    def test_private_scoreset_403_if_no_permission(self):
        obj = ScoreSet.objects.create(experiment=self.exp, private=True)
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        request = self.factory.get('/scoreset/')
        request.user = bob
        response = ScoresetDetailView.as_view()(
            request, accession=obj.accession)
        self.assertEqual(response.status_code, 403)

    def test_403_uses_template(self):
        obj = ScoreSet.objects.create(experiment=self.exp, private=True)
        response = self.client.get('/scoreset/{}/'.format(obj.accession))
        self.assertTemplateUsed(response, 'main/403_forbidden.html')

    def test_private_scoreset_rendered_if_user_can_view(self):
        obj = ScoreSet.objects.create(experiment=self.exp, private=False)
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        assign_perm(PermissionTypes.CAN_VIEW, bob, obj)

        request = self.factory.get('/scoreset/')
        request.user = bob
        response = ScoresetDetailView.as_view()(
            request, accession=obj.accession)
        self.assertEqual(response.status_code, 200)


class TestCreateNewScoreSetView(TestCase):
    """
    Test that the submission process does not allow invalid data through,
    and properly handles model creation.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.User = get_user_model()
        self.factory = RequestFactory()
        self.path = reverse_lazy("scoreset:scoreset_new")
        self.template = 'scoreset/new_scoreset.html'
        self.post_data = {
            'scoreset-experiment': [''],
            'scoreset-private': ['on'],
            'scoreset-abstract': [''],
            'scoreset-method_desc': [''],
            'scoreset-doi_id': [''],
            'scoreset-scores_data': [''],
            'scoreset-counts_data': [''],
            'keyword-TOTAL_FORMS': ['0'],
            'keyword-INITIAL_FORMS': ['0'],
            'keyword-MIN_NUM_FORMS': ['0'],
            'keyword-MAX_NUM_FORMS': ['1000'],
            'keyword-__prefix__-text': [''],
            'submit': ['submit']
        }

        self.exp_1 = Experiment.objects.create(
            target="test1", wt_sequence="AT")
        self.exp_2 = Experiment.objects.create(
            target="test2", wt_sequence="CG")

        self.username = "bob"
        self.password = "secret_key"
        self.bob = self.User.objects.create(username=self.username)
        self.bob.set_password(self.password)
        self.bob.save()
        self.client.logout()

    def test_redirect_to_login_not_logged_in(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)

    def test_can_submit_and_create_scoreset_when_forms_are_valid(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]
        data['keyword-TOTAL_FORMS'] = ['1']
        data['keyword-0-text'] = ['keyword']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)

        scs = ScoreSet.objects.all()[0]
        self.assertEqual(scs.keywords.count(), 1)
        self.assertEqual(scs.variant_set.count(), 1)

    def test_correct_tamplate_when_logged_in(self):
        self.client.login(
            username=self.username,
            password=self.password
        )
        response = self.client.get(self.path)
        self.assertTemplateUsed(response, self.template)

    def test_invalid_form_does_not_redirect(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = ['wrong_pk']
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertEqual(response.status_code, 200)

        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = [""]
        data['scoreset-counts_data'] = [""]
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertEqual(response.status_code, 200)

    def test_only_links_preexisting_keyword_and_doesnt_create(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]
        data['keyword-TOTAL_FORMS'] = ['2']
        data['keyword-0-text'] = ['keyword']
        data['keyword-1-text'] = ['keyword']
        request = self.factory.post(
            path=self.path,
            data=data
        )
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.all()[0].keywords.count(), 1)

    def test_blank_keywords_not_created(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]
        data['keyword-TOTAL_FORMS'] = ['1']
        data['keyword-0-text'] = [""]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertEqual(Keyword.objects.count(), 0)

    def test_scoreset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        scs = ScoreSet.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.bob, scs))

    def test_user_not_added_as_admin_to_scoreset_experiment(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        scs = ScoreSet.objects.all()[0]
        self.assertFalse(user_is_admin_for_instance(self.bob, scs.experiment))

    def test_private_dataset_request_returns_403(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        scs = ScoreSet.objects.all()[0]

        scores_dataset_path = '{}/{}/{}/'.format(
            self.path, scs.accession, 'scores')
        response = self.client.get(scores_dataset_path)
        self.assertEqual(response.status_code, 403)

        counts_dataset_path = '{}/{}/{}/'.format(
            self.path, scs.accession, 'counts')
        response = self.client.get(scores_dataset_path)
        self.assertEqual(response.status_code, 403)

    def test_private_metadata_request_returns_403(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-scores_data'] = ["hgvs,score\nstring,0.1"]
        data['scoreset-counts_data'] = ["hgvs,count\nstring,2"]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = scoreset_create_view(request)
        scs = ScoreSet.objects.all()[0]

        scores_dataset_path = '{}/{}/{}/'.format(
            self.path, scs.accession, 'metadata')
        response = self.client.get(scores_dataset_path)
        self.assertEqual(response.status_code, 403)
