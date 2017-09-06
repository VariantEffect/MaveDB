
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase, TransactionTestCase, RequestFactory
from django.test.client import Client

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login

from main.models import Keyword
from experiment.models import Experiment
from accounts.permissions import (
    user_is_admin_for_instance,
    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer
)

from scoreset.models import ScoreSet, Variant
from scoreset.views import (
    ScoreSetDetailView, scoreset_create_view,
    download_scoreset_data, download_scoreset_metadata
)

from .utility import make_score_count_files


class TestScoreSetSetDetailView(TestCase):
    """
    Test that experimentsets are displayed correctly to the public.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.User = get_user_model()
        self.factory = RequestFactory()
        self.exp = Experiment.objects.create(target="test", wt_sequence="AT")

    def test_404_status_and_template_used_when_object_not_found(self):
        response = self.client.get('/scoreset/{}/'.format("SCS999999A.1"))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'main/404_not_found.html')

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
        response = ScoreSetDetailView.as_view()(
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
        assign_user_as_instance_viewer(bob, obj)

        request = self.factory.get('/scoreset/')
        request.user = bob
        response = ScoreSetDetailView.as_view()(
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

        score_file, count_file = make_score_count_files()
        self.post_data = {
            'scoreset-experiment': [''],
            'scoreset-replaces': [''],
            'scoreset-private': ['on'],
            'scoreset-abstract': [''],
            'scoreset-method_desc': [''],
            'scoreset-doi_id': [''],
            'scoreset-scores_data': [score_file],
            'scoreset-counts_data': [count_file],
            'scoreset-keywords': [''],
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

    def test_experiment_options_are_restricted_to_admin_instances(self):
        assign_user_as_instance_admin(self.bob, self.exp_1)
        request = self.factory.get('/scoreset/new/')
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertContains(response, self.exp_1.accession)
        self.assertNotContains(response, self.exp_2.accession)

    def test_replaces_options_are_restricted_to_admin_instances(self):
        scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        scs_2 = ScoreSet.objects.create(experiment=self.exp_1)
        assign_user_as_instance_admin(self.bob, scs_1)

        request = self.factory.get('/scoreset/new/')
        request.user = self.bob
        response = scoreset_create_view(request)
        self.assertContains(response, scs_1.accession)
        self.assertNotContains(response, scs_2.accession)

    def test_can_submit_and_create_scoreset_when_forms_are_valid(self):
        data = self.post_data.copy()
        scs_1 = ScoreSet.objects.create(experiment=self.exp_1)
        assign_user_as_instance_admin(self.bob, scs_1)
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-replaces'] = [scs_1.pk]
        data['scoreset-keywords'] = ['test']

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(self.path, data=data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(Variant.objects.count(), 1)
        self.assertNotEqual(scs_1.replaced_by, None)

    def test_correct_tamplate_when_logged_in(self):
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(self.path)
        self.assertTemplateUsed(response, self.template)

    def test_invalid_form_does_not_redirect(self):
        data = self.post_data.copy()
        data['scoreset-experiment'] = ['wrong_pk']
        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)
        self.assertEqual(response.status_code, 200)

    def test_only_links_preexisting_keyword_and_doesnt_create(self):
        data = self.post_data.copy()
        Keyword.objects.create(text="test")
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-keywords'] = ['test']

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(ScoreSet.objects.all()[0].keywords.count(), 1)

    def test_blank_keywords_not_created(self):
        data = self.post_data.copy()
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]
        data['scoreset-keywords'] = ['']

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)
        self.assertEqual(Keyword.objects.count(), 0)

    def test_scoreset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)
        scs = ScoreSet.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.bob, scs))

    def test_private_dataset_request_returns_403(self):
        data = self.post_data.copy()
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)
        self.client.logout()

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
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)
        self.client.logout()

        scs = ScoreSet.objects.all()[0]
        scores_dataset_path = '{}/{}/{}/'.format(
            self.path, scs.accession, 'metadata')
        response = self.client.get(scores_dataset_path)
        self.assertEqual(response.status_code, 403)

    def test_download_returns_empty_response_if_no_counts_dataset(self):
        data = self.post_data.copy()
        assign_user_as_instance_admin(self.bob, self.exp_1)
        data['scoreset-experiment'] = [self.exp_1.pk]

        self.client.login(username=self.username, password=self.password)
        response = self.client.post(path=self.path, data=data)

        scs = ScoreSet.objects.all()[0]
        counts_dataset_path = '{}/{}/{}/'.format(
            self.path, scs.accession, 'counts')
        response = self.client.get(counts_dataset_path)
        self.assertNotContains(response, "hgvs")
