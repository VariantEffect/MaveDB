

from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase, TransactionTestCase, RequestFactory

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login

from guardian.shortcuts import assign_perm, remove_perm

from accounts.models import user_is_admin_for_instance, PermissionTypes

from main.models import (
    Keyword, ExternalAccession,
    TargetOrganism, ReferenceMapping
)
from experiment.models import Experiment, ExperimentSet
from experiment.views import (
    ExperimentDetailView, ExperimentSetDetailView,
    experiment_create_view
)


class TestExperimentSetDetailView(TestCase):
    """
    Test that experimentsets are displayed correctly to the public.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.User = get_user_model()
        self.factory = RequestFactory()

    def test_uses_correct_template(self):
        obj = ExperimentSet.objects.create(private=False)
        response = self.client.get('/experiment/{}/'.format(obj.accession))
        self.assertTemplateUsed(response, 'experiment/experimentset.html')

    def test_private_experiment_403_if_no_permission(self):
        obj = ExperimentSet.objects.create()
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        request = self.factory.get('/experiment/')
        request.user = bob
        response = ExperimentSetDetailView.as_view()(
            request, accession=obj.accession)
        self.assertEqual(response.status_code, 403)

    def test_403_uses_template(self):
        obj = ExperimentSet.objects.create()
        response = self.client.get('/experiment/{}/'.format(obj.accession))
        self.assertTemplateUsed(response, 'main/403_forbidden.html')

    def test_404_status_and_template_used_when_object_not_found(self):
        self.fail("Write this test!")

    def test_private_experiment_rendered_if_user_can_view(self):
        obj = ExperimentSet.objects.create()
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        assign_perm(PermissionTypes.CAN_VIEW, bob, obj)

        request = self.factory.get('/experiment/')
        request.user = bob
        response = ExperimentSetDetailView.as_view()(
            request, accession=obj.accession)
        self.assertEqual(response.status_code, 200)


class TestExperimentDetailView(TestCase):
    """
    Test that experiments are displayed correctly to the public.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.User = get_user_model()
        self.factory = RequestFactory()

    def test_uses_correct_template(self):
        exp = Experiment.objects.create(
            target="test", wt_sequence="atcg", private=False
        )
        response = self.client.get('/experiment/{}/'.format(exp.accession))
        self.assertTemplateUsed(response, 'experiment/experiment.html')

    def test_private_experiment_403_if_no_permission(self):
        exp = Experiment.objects.create(target="BRCA1", wt_sequence="ATCG")
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        request = self.factory.get('/experiment/')
        request.user = bob
        response = ExperimentDetailView.as_view()(
            request, accession=exp.accession)
        self.assertEqual(response.status_code, 403)

    def test_403_uses_template(self):
        exp = Experiment.objects.create(target="BRCA1", wt_sequence="ATCG")
        response = self.client.get('/experiment/{}/'.format(exp.accession))
        self.assertTemplateUsed(response, 'main/403_forbidden.html')

    def test_404_status_and_template_used_when_object_not_found(self):
        self.fail("Write this test!")

    def test_private_experiment_rendered_if_user_can_view(self):
        exp = Experiment.objects.create(target="BRCA1", wt_sequence="ATCG")
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        assign_perm(PermissionTypes.CAN_VIEW, bob, exp)

        request = self.factory.get('/experiment/')
        request.user = bob
        response = ExperimentDetailView.as_view()(
            request, accession=exp.accession)
        self.assertEqual(response.status_code, 200)


class TestCreateNewExperimentView(TestCase):
    """
    Test that the submission process does not allow invalid data through,
    and properly handles model creation.
    """

    def setUp(self):
        # Every test needs access to the request factory.
        self.User = get_user_model()
        self.factory = RequestFactory()
        self.path = reverse_lazy("experiment:experiment_new")
        self.template = 'experiment/new_experiment.html'
        self.post_data = {
            'experiment-experimentset': [''],
            'experiment-private': ['on'],
            'experiment-target': [''],
            'experiment-target_organism': [''],
            'experiment-wt_sequence': [''],
            'experiment-abstract': [''],
            'experiment-method_desc': [''],
            'experiment-sra_id': [''],
            'experiment-doi_id': [''],
            'keyword-TOTAL_FORMS': ['0'],
            'keyword-INITIAL_FORMS': ['0'],
            'keyword-MIN_NUM_FORMS': ['0'],
            'keyword-MAX_NUM_FORMS': ['1000'],
            'keyword-__prefix__-text': [''],
            'external_accession-TOTAL_FORMS': ['0'],
            'external_accession-INITIAL_FORMS': ['0'],
            'external_accession-MIN_NUM_FORMS': ['0'],
            'external_accession-MAX_NUM_FORMS': ['1000'],
            'external_accession-__prefix__-text': [''],
            'reference_mapping-TOTAL_FORMS': ['0'],
            'reference_mapping-INITIAL_FORMS': ['0'],
            'reference_mapping-MIN_NUM_FORMS': ['0'],
            'reference_mapping-MAX_NUM_FORMS': ['1000'],
            'reference_mapping-__prefix__-reference': [''],
            'reference_mapping-__prefix__-target_start': [''],
            'reference_mapping-__prefix__-target_end': [''],
            'reference_mapping-__prefix__-reference_start': [''],
            'reference_mapping-__prefix__-reference_end': [''],
            'submit': ['submit']
        }

        self.username = "bob"
        self.password = "secret_key"
        self.bob = self.User.objects.create(username=self.username)
        self.bob.set_password(self.password)
        self.bob.save()
        self.client.logout()

    def test_redirect_to_login_not_logged_in(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)

    def test_can_submit_and_create_experiment_when_forms_are_valid(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"
        data['experiment-target_organism'] = "Homo sapiens"
        data['keyword-TOTAL_FORMS'] = ['1']
        data['keyword-0-text'] = ['keyword']
        data['external_accession-TOTAL_FORMS'] = ['1']
        data['external_accession-0-text'] = ['accession']
        data['reference_mapping-TOTAL_FORMS'] = ['1']
        data['reference_mapping-0-reference'] = ['reference']
        data['reference_mapping-0-is_alternate'] = ['off']
        data['reference_mapping-0-target_start'] = [0]
        data['reference_mapping-0-target_end'] = [10]
        data['reference_mapping-0-reference_start'] = [0]
        data['reference_mapping-0-reference_end'] = [10]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(ExternalAccession.objects.count(), 1)
        self.assertEqual(TargetOrganism.objects.count(), 1)
        self.assertEqual(ReferenceMapping.objects.count(), 1)

        e = Experiment.objects.all()[0]
        self.assertEqual(e.keywords.count(), 1)
        self.assertEqual(e.external_accessions.count(), 1)
        self.assertEqual(e.target_organism.count(), 1)
        self.assertEqual(ReferenceMapping.objects.all()[0].experiment.pk, e.pk)

    def test_correct_tamplate_when_logged_in(self):
        self.client.login(
            username=self.username,
            password=self.password
        )
        response = self.client.get(self.path)
        self.assertTemplateUsed(response, self.template)

    def test_invalid_form_does_not_redirect(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = ""  # required field missing
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

        data['reference_mapping-TOTAL_FORMS'] = ['1']
        data['reference_mapping-0-reference'] = ['reference']
        data['experiment-wt_sequence'] = "atcg"
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

    def test_only_links_preexisting_keyword_and_doesnt_create(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"
        data['keyword-TOTAL_FORMS'] = ['2']
        data['keyword-0-text'] = ['keyword']
        data['keyword-1-text'] = ['keyword']
        request = self.factory.post(
            path=self.path,
            data=data
        )
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(Experiment.objects.all()[0].keywords.count(), 1)

    def test_only_links_preexisting_target_organism_and_doesnt_create(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"

        # Create first experiment
        data['experiment-target_organism'] = "Homo sapiens"
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)

        # Create second experiment with same target organism
        data['experiment-target_organism'] = "Homo sapiens"
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        e1, e2 = list(Experiment.objects.all())
        self.assertEqual(TargetOrganism.objects.count(), 1)
        self.assertEqual(
            e1.target_organism.all()[0].pk,
            e2.target_organism.all()[0].pk
        )

    def test_only_links_preexisting_accession_and_doesnt_create(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"
        data['external_accession-TOTAL_FORMS'] = ['2']
        data['external_accession-0-text'] = ['acc']
        data['external_accession-1-text'] = ['acc']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ExternalAccession.objects.count(), 1)
        self.assertEqual(
            Experiment.objects.all()[0].external_accessions.count(), 1
        )

    def test_multiple_ref_maps_will_be_created(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"

        data['reference_mapping-TOTAL_FORMS'] = ['2']
        data['reference_mapping-0-reference'] = ['reference']
        data['reference_mapping-0-is_alternate'] = ['off']
        data['reference_mapping-0-target_start'] = [0]
        data['reference_mapping-0-target_end'] = [10]
        data['reference_mapping-0-reference_start'] = [0]
        data['reference_mapping-0-reference_end'] = [10]

        data['reference_mapping-1-reference'] = ['reference']
        data['reference_mapping-1-is_alternate'] = ['off']
        data['reference_mapping-1-target_start'] = [0]
        data['reference_mapping-1-target_end'] = [10]
        data['reference_mapping-1-reference_start'] = [0]
        data['reference_mapping-1-reference_end'] = [10]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ReferenceMapping.objects.count(), 2)

    def test_blank_keywords_not_created(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"
        data['keyword-TOTAL_FORMS'] = ['1']
        data['keyword-0-text'] = [""]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(Keyword.objects.count(), 0)

    def test_blank_target_organism_not_created(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-target_organism'] = ""
        data['experiment-wt_sequence'] = "atcg"
        data['keyword-TOTAL_FORMS'] = ['1']
        data['keyword-0-text'] = [""]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(TargetOrganism.objects.count(), 0)

    def test_blank_external_accessions_not_created(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"
        data['external_accession-TOTAL_FORMS'] = ['1']
        data['external_accession-0-text'] = [""]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ExternalAccession.objects.count(), 0)

    def test_blank_ref_map_not_created(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"
        data['reference_mapping-TOTAL_FORMS'] = ['1']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ReferenceMapping.objects.count(), 0)

    def test_experiment_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        e = Experiment.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.bob, e))

    def test_experimentset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        es = ExperimentSet.objects.all()[0]
        self.assertTrue(response.status_code, 302)
        self.assertTrue(user_is_admin_for_instance(self.bob, es))

    def test_selected_experimentset_does_not_add_user_as_admin(self):
        data = self.post_data.copy()
        es = ExperimentSet.objects.create()
        data['experiment-experimentset'] = es.pk
        data['experiment-target'] = "brca1"
        data['experiment-wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertTrue(response.status_code, 302)
        self.assertFalse(user_is_admin_for_instance(self.bob, es))
