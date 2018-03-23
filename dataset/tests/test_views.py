

from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase, TransactionTestCase, RequestFactory

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login

from accounts.permissions import (
    user_is_admin_for_instance,
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer
)

from metadata.models import Keyword, ExternalIdentifier

from genome.models import (
    ReferenceGenome, TargetOrganism, TargetGene, WildTypeSequence
)

from dataset.models import Experiment, ExperimentSet
from dataset.views import (
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
        response = self.client.get('/experiment/{}/'.format("EXPS999999"))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'main/404_not_found.html')

    def test_private_experiment_rendered_if_user_can_view(self):
        obj = ExperimentSet.objects.create()
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        assign_user_as_instance_viewer(bob, obj)
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
        response = self.client.get('/experiment/{}/'.format("EXP999999A"))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'main/404_not_found.html')

    def test_private_experiment_rendered_if_user_can_view(self):
        exp = Experiment.objects.create(target="BRCA1", wt_sequence="ATCG")
        bob = self.User.objects.create_user(
            username='bob', password='top_secret'
        )
        assign_user_as_instance_viewer(bob, exp)
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
            'experimentset': [''],
            'private': ['on'],
            'target': [''],
            'target_organism': [''],
            'wt_sequence': [''],
            'abstract': [''],
            'method_desc': [''],
            'sra_id': [''],
            'doi_id': [''],
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

    def test_experimentset_options_are_restricted_to_admin_instances(self):
        data = self.post_data.copy()
        exps_1 = ExperimentSet.objects.create()
        exps_2 = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.bob, exps_1)

        request = self.factory.get('/experiment/new/')
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertContains(response, exps_1.accession)
        self.assertNotContains(response, exps_2.accession)

    def test_can_submit_and_create_experiment_when_forms_are_valid(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['target_organism'] = ["Homo sapiens"]
        data['keywords'] = ['test']
        data['external_accessions'] = ['test']
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
        self.assertEqual(Keyword.objects.count(), 1)
        self.assertEqual(ExternalIdentifier.objects.count(), 1)
        self.assertEqual(TargetOrganism.objects.count(), 1)
        self.assertEqual(ReferenceGenome.objects.count(), 1)

        e = Experiment.objects.all()[0]
        self.assertEqual(e.keywords.count(), 1)
        self.assertEqual(e.external_accessions.count(), 1)
        self.assertEqual(e.target_organism.count(), 1)
        self.assertEqual(ReferenceGenome.objects.all()[0].experiment.pk, e.pk)

    def test_correct_tamplate_when_logged_in(self):
        self.client.login(
            username=self.username,
            password=self.password
        )
        response = self.client.get(self.path)
        self.assertTemplateUsed(response, self.template)

    def test_invalid_form_does_not_redirect(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = ""  # required field missing
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

        data['reference_mapping-TOTAL_FORMS'] = ['1']
        data['reference_mapping-0-reference'] = ['reference']
        data['wt_sequence'] = "atcg"
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(response.status_code, 200)

    def test_only_links_preexisting_keyword_and_doesnt_create(self):
        data = self.post_data.copy()
        Keyword.objects.create(text='test1')
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['keywords'] = ['test1']
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
        TargetOrganism.objects.create(text='Homo sapiens')
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"

        # Create first experiment
        data['target_organism'] = "Homo sapiens"
        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)

        # Create second experiment with same target organism
        data['target_organism'] = "Homo sapiens"
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
        ExternalIdentifier.objects.create(text='test1')
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['external_accessions'] = ["test1"]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ExternalIdentifier.objects.count(), 1)
        self.assertEqual(
            Experiment.objects.all()[0].external_accessions.count(), 1
        )

    def test_multiple_ref_maps_will_be_created(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"

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
        data['reference_mapping-1-target_end'] = [50]
        data['reference_mapping-1-reference_start'] = [0]
        data['reference_mapping-1-reference_end'] = [600]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ReferenceGenome.objects.count(), 2)

    def test_only_keep_one_ref_map_if_duplicates_supplied(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"

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
        self.assertEqual(ReferenceGenome.objects.count(), 1)

    def test_blank_keywords_not_created(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['keywords'] = ['']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(Keyword.objects.count(), 0)

    def test_blank_target_organism_not_created(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['target_organism'] = ""
        data['wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(TargetOrganism.objects.count(), 0)

    def test_blank_external_accessions_not_created(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['external_accessions'] = ['']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ExternalIdentifier.objects.count(), 0)

    def test_blank_ref_map_not_created(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['reference_mapping-TOTAL_FORMS'] = ['1']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ReferenceGenome.objects.count(), 0)

    def test_experiment_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        e = Experiment.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.bob, e))

    def test_experimentset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        es = ExperimentSet.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.bob, es))

    def test_selected_experimentset_does_not_add_user_as_admin(self):
        data = self.post_data.copy()
        es = ExperimentSet.objects.create()
        data['experimentset'] = es.pk
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertFalse(user_is_admin_for_instance(self.bob, es))

    def test_can_create_new_keywords(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['keywords'] = ['test']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(Keyword.objects.count(), 1)

    def test_can_create_new_ext_accessions(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['wt_sequence'] = "atcg"
        data['external_accessions'] = ['test']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(ExternalIdentifier.objects.count(), 1)

    def test_can_create_new_target_orgs(self):
        data = self.post_data.copy()
        data['target'] = "brca1"
        data['target_organism'] = ['test']
        data['wt_sequence'] = "atcg"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.bob
        response = experiment_create_view(request)
        self.assertEqual(TargetOrganism.objects.count(), 1)