from django.test import TestCase, RequestFactory
from django.urls import reverse_lazy

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_viewer,
    assign_user_as_instance_admin,
    assign_user_as_instance_editor,
    user_is_admin_for_instance
)

from metadata.factories import (
    SraIdentifierFactory, DoiIdentifierFactory,
    PubmedIdentifierFactory, KeywordFactory
)

from ..models.experiment import Experiment
from ..models.experimentset import ExperimentSet
from ..factories import ExperimentFactory, ExperimentSetFactory
from ..views.experiment import ExperimentDetailView, experiment_create_view


class TestExperimentDetailView(TestCase):
    """
    Test that experiments are displayed correctly to the public.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'dataset/experiment/experiment.html'
        self.template_403 = 'main/403_forbidden.html'
        self.template_404 = 'main/404_not_found.html'

    def test_uses_correct_template(self):
        obj = ExperimentFactory()
        obj.publish()
        obj.save()
        response = self.client.get('/experiment/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template)

    def test_private_instance_will_403_if_no_permission(self):
        user = UserFactory()
        obj = ExperimentFactory(private=True)
        request = self.factory.get('/experiment/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_403_uses_correct_template(self):
        obj = ExperimentFactory(private=True)
        response = self.client.get('/experiment/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template_403)

    def test_404_status_and_template_used_when_object_not_found(self):
        obj = ExperimentFactory()
        urn = obj.urn
        obj.delete()
        response = self.client.get('/experiment/{}/'.format(urn))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'main/404_not_found.html')

    def test_private_experiment_rendered_if_user_can_view(self):
        user = UserFactory()
        obj = ExperimentFactory()
        assign_user_as_instance_viewer(user, obj)
        request = self.factory.get('/experiment/{}/'.format(obj.urn))
        request.user = user
        response = ExperimentDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)


class TestCreateNewExperimentView(TestCase):
    """
    Test that the submission process does not allow invalid data through,
    and properly handles model creation.
    """
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.template = 'dataset/experiment/new_experiment.html'
        self.template_403 = 'main/403_forbidden.html'
        self.template_404 = 'main/404_not_found.html'
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
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'error')

    def test_form_will_post_with_valid_data(self):
        data = self.post_data
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.keywords.count(), 2)
        self.assertEqual(experiment.abstract_text, 'hello world')
        self.assertEqual(experiment.method_text, 'foo bar')

    def test_valid_submission_sets_created_by(self):
        data = self.post_data
        exps = ExperimentSetFactory()
        assign_user_as_instance_admin(self.user, exps)
        data['experimentset'] = [exps.pk]
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

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
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.parent, exps)
        self.assertEqual(experiment.modified_by, self.user)
        self.assertIsNone(experiment.parent.modified_by, None)

    def test_valid_submission_sets_parent_created_by(self):
        data = self.post_data
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.created_by, self.user)
        self.assertEqual(experiment.parent.created_by, self.user)

    def test_valid_submission_sets_parent_modified_by(self):
        data = self.post_data
        data['abstract_text'] = ['hello world']
        data['method_text'] = ['foo bar']
        data['keywords'] = ['protein', 'blue']
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

        experiment = Experiment.objects.first()
        self.assertEqual(experiment.modified_by, self.user)
        self.assertEqual(experiment.parent.modified_by, self.user)

    def test_experiment_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        _ = experiment_create_view(request)
        exp = Experiment.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.user, exp))

    def test_new_experimentset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        _ = experiment_create_view(request)
        exps = ExperimentSet.objects.first()

        self.assertTrue(user_is_admin_for_instance(self.user, exps))

    def test_selected_experimentset_does_not_add_user_as_admin(self):
        data = self.post_data.copy()
        es = ExperimentSetFactory()
        assign_user_as_instance_editor(self.user, es)
        data['experimentset'] = [es.pk]
        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        _ = experiment_create_view(request)

        self.assertFalse(user_is_admin_for_instance(self.user, es))

    def test_failed_submission_adds_keywords_to_context(self):
        data = self.post_data.copy()
        kw = KeywordFactory()
        data['keywords'] = ['protein', kw.text]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = experiment_create_view(request)

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

            request = self.factory.post(path=self.path, data=data)
            request.user = self.user
            response = experiment_create_view(request)

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
            instance.delete()

            request = self.factory.post(path=self.path, data=data)
            request.user = self.user
            response = experiment_create_view(request)

            self.assertContains(response, instance.identifier)
