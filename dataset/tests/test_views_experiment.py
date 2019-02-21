from django.test import TestCase, RequestFactory, mock
from django.urls import reverse_lazy
from django.http import Http404
from django.core.exceptions import PermissionDenied

from reversion.models import Version

from core.utilities.tests import TestMessageMixin

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_viewer,
    assign_user_as_instance_admin,
    assign_user_as_instance_editor,
)

from metadata.factories import (
    SraIdentifierFactory, DoiIdentifierFactory,
    PubmedIdentifierFactory, KeywordFactory
)

from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet
from ..factories import ExperimentFactory, ExperimentSetFactory
from ..views.experiment import (
    ExperimentDetailView, ExperimentCreateView, ExperimentEditView
)


class TestExperimentDetailView(TestCase, TestMessageMixin):
    """
    Test that experiments are displayed correctly to the public.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'dataset/experiment/experiment.html'
        self.template_403 = 'main/403.html'
        self.template_404 = 'main/404.html'

    def test_uses_correct_template(self):
        obj = ExperimentFactory(
            private=False,
            experimentset__private=False
        )
        response = self.client.get('/experiment/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template)

    def test_private_instance_will_403_if_no_permission(self):
        user = UserFactory()
        obj = ExperimentFactory(private=True)
        request = self.create_request(
            method='get', path='/experiment/{}/'.format(obj.urn))
        request.user = user
        with self.assertRaises(PermissionDenied):
            ExperimentDetailView.as_view()(request, urn=obj.urn)

    def test_403_no_permission_if_private(self):
        obj = ExperimentFactory(private=True)
        request = self.create_request(
            method='get', path='/experiment/{}/'.format(obj.urn))
        request.user = UserFactory()
        with self.assertRaises(PermissionDenied):
            ExperimentDetailView.as_view()(request, urn=obj.urn)

    def test_404_status_and_template_used_when_object_not_found(self):
        user = UserFactory()
        obj = ExperimentFactory()
        assign_user_as_instance_admin(user, obj)

        urn = obj.urn
        obj.delete()

        request = self.create_request(
            method='get', path='/experiment/{}/'.format(urn))
        request.user = user
        with self.assertRaises(Http404):
            ExperimentDetailView.as_view()(request, urn=obj.urn)

    def test_private_experiment_rendered_if_user_can_view(self):
        user = UserFactory()
        obj = ExperimentFactory()
        assign_user_as_instance_viewer(user, obj)
        request = self.create_request(
            method='get', path='/experiment/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)
        
    def test_user_with_edit_permission_can_see_add_and_edit_button(self):
        user = UserFactory()
        obj = ExperimentFactory()
        assign_user_as_instance_editor(user, obj)
        request = self.create_request(
            method='get', path='/experiment/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentDetailView.as_view()(request, urn=obj.urn)
        self.assertContains(response, 'Add a score set')
        self.assertContains(response, 'Edit this experiment')
        
    def test_user_without_edit_permission_cannot_see_edit_button(self):
        user = UserFactory()
        obj = ExperimentFactory()
        assign_user_as_instance_viewer(user, obj)
        request = self.create_request(
            method='get', path='/experiment/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentDetailView.as_view()(request, urn=obj.urn)
        self.assertNotContains(response, 'Add a score set')
        self.assertNotContains(response, 'Edit this experiment')
        

class TestCreateNewExperimentView(TestCase, TestMessageMixin):
    """
    Test that the submission process does not allow invalid data through,
    and properly handles model creation.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.template = 'dataset/experiment/new_experiment.html'
        self.template_403 = 'main/403.html'
        self.template_404 = 'main/404.html'
        self.path = reverse_lazy("dataset:experiment_new")
        self.post_data = {
            'experimentset': [''],
            'private': ['on'],
            'abstract_text': [''],
            'method_text': [''],
            'short_description': ['experiment'],
            'title': ['title'],
            'sra_ids': [''],
            'doi_ids': [''],
            'pubmed_ids': [''],
            'keywords': [''],
            'submit': ['submit']
        }
        self.unencrypted_password = 'secret_key'
        self.user = UserFactory(password=self.unencrypted_password)
        self.user.set_password(self.unencrypted_password)
        self.user.save()
        self.client.logout()
        
    def tearDown(self):
        Version.objects.all().delete()

    def test_redirect_to_login_not_logged_in(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)

    def test_correct_tamplate_when_logged_in(self):
        self.client.login(
            username=self.user.username,
            password=self.unencrypted_password
        )
        response = self.client.get(self.path)
        self.assertTemplateUsed(response, self.template)

    def test_invalid_form_does_not_redirect(self):
        data = self.post_data
        data['target'] = "brca1"
        data['title'] = ""  # Required field missing
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_form_will_post_with_valid_data(self):
        data = self.post_data
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.keywords.count(), 2)
        self.assertEqual(experiment.abstract_text, 'hello world')
        self.assertEqual(experiment.method_text, 'foo bar')

    def test_creates_new_reversion_instances_for_exp_and_exps(self):
        data = self.post_data.copy()
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        self.assertEqual(Version.objects.count(), 0)
        ExperimentCreateView.as_view()(request)
        self.assertEqual(Version.objects.count(), 2)

    def test_valid_submission_sets_created_by(self):
        data = self.post_data
        exps = ExperimentSetFactory()
        assign_user_as_instance_admin(self.user, exps)
        data['experimentset'] = [exps.pk]
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.parent, exps)
        self.assertEqual(experiment.created_by, self.user)
        self.assertIsNone(experiment.parent.created_by, None)

    def test_valid_submission_sets_modified_by(self):
        data = self.post_data
        exps = ExperimentSetFactory()
        assign_user_as_instance_admin(self.user, exps)
        data['experimentset'] = [exps.pk]
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.parent, exps)
        self.assertEqual(experiment.modified_by, self.user)
        self.assertIsNone(experiment.parent.modified_by, None)

    def test_valid_submission_sets_parent_created_by(self):
        data = self.post_data
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.created_by, self.user)
        self.assertEqual(experiment.parent.created_by, self.user)

    def test_valid_submission_sets_parent_modified_by(self):
        data = self.post_data
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.modified_by, self.user)
        self.assertEqual(experiment.parent.modified_by, self.user)

    def test_experiment_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        request = self.create_request(path=self.path, data=data, method='post')
        request.user = self.user
        _ = ExperimentCreateView.as_view()(request)
        exp = Experiment.objects.all()[0]
        self.assertTrue(self.user in exp.administrators)

    def test_new_experimentset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        _ = ExperimentCreateView.as_view()(request)
        exps = ExperimentSet.objects.first()

        self.assertTrue(self.user in exps.administrators)

    def test_selected_experimentset_does_not_add_user_as_admin(self):
        data = self.post_data.copy()
        es = ExperimentSetFactory()
        assign_user_as_instance_editor(self.user, es)
        data['experimentset'] = [es.pk]
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        _ = ExperimentCreateView.as_view()(request)

        self.assertFalse(self.user in es.administrators)

    def test_failed_submission_adds_keywords_to_context(self):
        data = self.post_data.copy()
        kw = KeywordFactory()
        data['keywords'] = ['protein', kw.text]
        data['title'] = ""

        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)

        self.assertContains(response, 'protein')
        self.assertContains(response, kw.text)

    def test_failed_submission_adds_extern_identifier_to_context(self):
        fs = [
            (SraIdentifierFactory, 'sra_ids'),
            (PubmedIdentifierFactory, 'pubmed_ids'),
            (DoiIdentifierFactory, 'doi_ids')
        ]
        for factory, field in fs:
            data = self.post_data.copy()
            instance = factory()
            data[field] = [instance.identifier]
            data['title'] = ""

            request = self.create_request(
                method='post', path=self.path, data=data)
            request.user = self.user
            response = ExperimentCreateView.as_view()(request)

            self.assertContains(response, instance.identifier)

    def test_failed_submission_adds_new_extern_identifier_to_context(self):
        fs = [
            (SraIdentifierFactory, 'sra_ids'),
            (PubmedIdentifierFactory, 'pubmed_ids'),
            (DoiIdentifierFactory, 'doi_ids')
        ]
        for factory, field in fs:
            data = self.post_data.copy()
            instance = factory()
            value = instance.identifier
            data[field] = [value]
            data['title'] = ""
            instance.delete()

            request = self.create_request(
                method='post', path=self.path, data=data)
            request.user = self.user
            response = ExperimentCreateView.as_view()(request)

            self.assertContains(response, instance.identifier)

    def test_GET_experimentset_param_locks_experiment_choice(self):
        exp1 = ExperimentSetFactory()
        exp2 = ExperimentSetFactory()
        assign_user_as_instance_editor(self.user, exp1)
        assign_user_as_instance_editor(self.user, exp2)
        request = self.factory.get(
            path=self.path + '/?experimentset={}'.format(exp1.urn))
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertContains(response, exp1.urn)
        self.assertNotContains(response, exp2.urn)

    def test_GET_experimentset_param_ignored_if_no_edit_permissions(self):
        exp1 = ExperimentSetFactory()
        exp2 = ExperimentSetFactory()
        assign_user_as_instance_editor(self.user, exp2)
        request = self.factory.get(
            path=self.path + '/?experimentset={}'.format(exp1.urn))
        request.user = self.user
        response = ExperimentCreateView.as_view()(request)
        self.assertNotContains(response, exp1.urn)
        self.assertContains(response, exp2.urn)


class TestEditExperimentView(TestCase, TestMessageMixin):
    """
    Test that the submission process does not allow invalid data through,
    and properly handles model creation.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.path = '/profile/edit/experiment/{}/'
        self.template = 'dataset/experiment/update_experiment.html'
        self.post_data = {
            'experimentset': [''],
            'private': ['on'],
            'abstract_text': [''],
            'method_text': [''],
            'short_description': ['experiment'],
            'title': ['title'],
            'sra_ids': [''],
            'doi_ids': [''],
            'pubmed_ids': [''],
            'keywords': [''],
            'submit': ['submit']
        }
        self.unencrypted_password = 'secret_key'
        self.user = UserFactory(password=self.unencrypted_password)
        self.user.set_password(self.unencrypted_password)
        self.user.save()
        self.client.logout()
        
    def tearDown(self):
        Version.objects.all().delete()

    def test_correct_tamplate_when_logged_in(self):
        scs = ExperimentFactory()
        assign_user_as_instance_admin(self.user, scs)
        self.client.login(
            username=self.user.username,
            password=self.unencrypted_password
        )
        response = self.client.get(self.path.format(scs.urn))
        self.assertTemplateUsed(response, self.template)

    def test_requires_login(self):
        self.client.logout()
        obj = ExperimentFactory()
        response = self.client.get(self.path.format(obj.urn))
        self.assertEqual(response.status_code, 302)

    def test_404_object_not_found(self):
        obj = ExperimentFactory()
        urn = obj.urn
        request = self.factory.get(self.path.format(urn))
        request.user = self.user
        obj.delete()
        with self.assertRaises(Http404):
            ExperimentEditView.as_view()(request, urn=urn)

    def test_redirect_to_profile_if_no_permission(self):
        exp = ExperimentFactory()
        assign_user_as_instance_viewer(self.user, exp)

        path = self.path.format(exp.urn)
        request = self.create_request(method='get', path=path)
        request.user = self.user

        response = ExperimentEditView.as_view()(request, urn=exp.urn)
        self.assertEqual(response.status_code, 302)

    def test_published_instance_returns_edit_only_mode_form(self):
        exp = ExperimentFactory(private=False)
        assign_user_as_instance_admin(self.user, exp)
        assign_user_as_instance_admin(self.user, exp.parent)

        path = self.path.format(exp.urn)
        request = self.create_request(method='get', path=path)
        request.user = self.user

        response = ExperimentEditView.as_view()(request, urn=exp.urn)
        self.assertNotContains(response, 'id_experimentset')

    def test_valid_submission_sets_modified_by(self):
        data = self.post_data
        exp = ExperimentFactory(private=False)
        assign_user_as_instance_admin(self.user, exp)
        assign_user_as_instance_admin(self.user, exp.parent)

        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        response = ExperimentEditView.as_view()(request, urn=exp.urn)
        self.assertEqual(response.status_code, 302)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.modified_by, self.user)

    def test_experimentset_options_are_restricted_to_editor_instances(self):
        exp1 = ExperimentFactory()
        exp2 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        assign_user_as_instance_editor(self.user, exp1.parent)
        assign_user_as_instance_viewer(self.user, exp2.parent)

        request = self.create_request(method='get', path=self.path)
        request.user = self.user
        response = ExperimentEditView.as_view()(request, urn=exp1.urn)

        self.assertContains(
            response, '{}'.format(exp1.parent.urn, exp1.parent.title))
        self.assertNotContains(
            response, '{}'.format(exp2.parent.urn, exp2.parent.title))

    def test_experimentset_options_are_restricted_to_admin_instances(self):
        exp1 = ExperimentFactory()
        exp2 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        assign_user_as_instance_admin(self.user, exp1.parent)
        assign_user_as_instance_viewer(self.user, exp2.parent)

        request = self.create_request(method='get', path=self.path)
        request.user = self.user
        response = ExperimentEditView.as_view()(request, urn=exp1.urn)

        self.assertContains(
            response, '{}'.format(exp1.parent.urn, exp1.parent.title))
        self.assertNotContains(
            response, '{}'.format(exp2.parent.urn, exp2.parent.title))

    def test_creates_new_reversion_instances_for_exp_and_exps(self):
        data = self.post_data
        exp = ExperimentFactory(private=False)
        assign_user_as_instance_admin(self.user, exp)
        assign_user_as_instance_admin(self.user, exp.parent)

        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user
        
        self.assertEqual(Version.objects.count(), 0)
        ExperimentEditView.as_view()(request, urn=exp.urn)
        self.assertEqual(Version.objects.count(), 1)
