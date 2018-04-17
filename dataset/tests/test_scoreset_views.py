from django.core import mail
from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory

from accounts.factories import UserFactory
from accounts.permissions import (
    assign_user_as_instance_viewer,
    assign_user_as_instance_editor,
    assign_user_as_instance_admin,
    user_is_admin_for_instance
)

from genome.models import WildTypeSequence, TargetGene
from genome.factories import ReferenceGenomeFactory

from metadata.factories import (
    KeywordFactory, PubmedIdentifierFactory, DoiIdentifierFactory,
    SraIdentifierFactory
)

from variant.factories import VariantFactory

import dataset.constants as constants
from ..factories import ScoreSetFactory, ExperimentFactory
from ..models.scoreset import ScoreSet
from ..views.scoreset import ScoreSetDetailView, scoreset_create_view

from .utility import make_score_count_files


class TestScoreSetSetDetailView(TestCase):
    """
    Test that experimentsets are displayed correctly to the public.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'dataset/scoreset/scoreset.html'
        self.template_403 = 'main/403_forbidden.html'
        self.template_404 = 'main/404_not_found.html'

    def test_404_status_and_template_used_when_object_not_found(self):
        obj = ScoreSetFactory()
        urn = obj.urn
        obj.delete()
        response = self.client.get('/scoreset/{}/'.format(urn))
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, self.template_404)

    def test_uses_correct_template(self):
        obj = ScoreSetFactory()
        obj.publish()
        obj.save()
        response = self.client.get('/scoreset/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template)

    def test_private_instance_will_403_if_no_permission(self):
        user = UserFactory()
        obj = ScoreSetFactory(private=True)
        request = self.factory.get('/scoreset/{}/'.format(obj.urn))
        request.user = user
        response = ScoreSetDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_403_uses_correct_template(self):
        obj = ScoreSetFactory(private=True)
        response = self.client.get('/scoreset/{}/'.format(obj.urn))
        self.assertTemplateUsed(response, self.template_403)

    def test_private_experiment_rendered_if_user_can_view(self):
        user = UserFactory()
        obj = ScoreSetFactory()
        assign_user_as_instance_viewer(user, obj)
        request = self.factory.get('/scoreset/{}/'.format(obj.urn))
        request.user = user
        response = ScoreSetDetailView.as_view()(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)

    def test_variants_are_in_response(self):
        scs = ScoreSetFactory()
        var = VariantFactory(scoreset=scs)
        scs.publish()
        scs.save()
        request = self.factory.get('/scoreset/{}/'.format(scs.urn))
        request.user = UserFactory()
        response = ScoreSetDetailView.as_view()(request, urn=scs.urn)
        self.assertContains(response, var.hgvs)


class TestCreateNewScoreSetView(TestCase):
    """
    Test that the submission process does not allow invalid data through,
    and properly handles model creation.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.path = reverse_lazy("dataset:scoreset_new")
        self.template = 'dataset/scoreset/new_scoreset.html'
        self.ref = ReferenceGenomeFactory()

        score_file, _ = make_score_count_files()
        self.post_data = {
            'experiment': [''],
            'replaces': [''],
            'private': ['on'],
            'short_description': 'an entry',
            'title': 'title',
            'abstract_text': [''],
            'method_text': [''],
            'sra_ids': [''],
            'doi_ids': [''],
            'pubmed_ids': [''],
            'keywords': [''],
            'submit': ['submit'],
            'start': [1],
            'end': [2],
            'chromosome': ['chrX'],
            'strand': ['F'],
            'genome': [self.ref.pk],
            'is_primary': True,
            'wt_sequence': 'atcg',
            'name': 'BRCA1',
            "publish": ['']
        }
        self.files = {constants.variant_score_data: score_file}
        self.user = UserFactory()
        self.username = self.user.username
        self.unencrypted_password = 'secret_key'
        self.user.set_password(self.unencrypted_password)
        self.user.save()
        self.client.logout()

    def test_redirect_to_login_not_logged_in(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)

    def test_correct_tamplate_when_logged_in(self):
        self.client.login(
            username=self.username,
            password=self.unencrypted_password
        )
        response = self.client.get(self.path)
        self.assertTemplateUsed(response, self.template)

    def test_annotation_and_intervals_created(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        response = scoreset_create_view(request)

        # Redirects to scoreset_detail
        self.assertEqual(response.status_code, 302)

        scoreset = ScoreSet.objects.order_by("-urn").first()
        self.assertIsNotNone(scoreset.get_target())
        targetgene = scoreset.get_target()

        annotation = targetgene.get_annotations().first()
        genome = annotation.get_reference_genome()
        interval = annotation.get_intervals().first()

        self.assertEqual(genome.get_short_name(), self.ref.get_short_name())
        self.assertEqual(genome.get_species_name(), self.ref.get_species_name())

        self.assertEqual(
            interval.serialise(),
            {'start': 1, 'end': 2, 'chromosome': 'chrX', 'strand': 'F'}
        )

    def test_experiment_options_are_restricted_to_admin_instances(self):
        exp1 = ExperimentFactory()
        exp2 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        request = self.factory.get('/scoreset/new/')
        request.user = self.user

        response = scoreset_create_view(request)
        self.assertContains(response, exp1.urn)
        self.assertNotContains(response, exp2.urn)

    def test_replaces_options_are_restricted_to_admin_instances(self):
        exp1 = ExperimentFactory()
        scs_1 = ScoreSetFactory(experiment=exp1)
        scs_2 = ScoreSetFactory(experiment=exp1)
        assign_user_as_instance_admin(self.user, scs_1)

        request = self.factory.get('/scoreset/new/')
        request.user = self.user

        response = scoreset_create_view(request)
        self.assertContains(response, scs_1.urn)
        self.assertNotContains(response, scs_2.urn)

    def test_can_submit_and_create_scoreset_when_forms_are_valid(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        scs1 = ScoreSetFactory(experiment=exp1)
        assign_user_as_instance_admin(self.user, scs1)
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]
        data['replaces'] = [scs1.pk]
        data['keywords'] = ['protein', 'kinase']
        data['abstract_text'] = "Hello world"
        data['method_text'] = "foo bar"

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        response = scoreset_create_view(request)

        # Redirects to scoreset_detail
        self.assertEqual(response.status_code, 302)

        scoreset = ScoreSet.objects.order_by("-urn").first()
        self.assertEqual(scoreset.experiment, exp1)
        self.assertEqual(scoreset.replaces, scs1)
        self.assertEqual(scoreset.keywords.count(), 2)
        self.assertEqual(scoreset.abstract_text, 'Hello world')
        self.assertEqual(scoreset.method_text, 'foo bar')

    def test_invalid_form_does_not_redirect(self):
        data = self.post_data.copy()
        data['experiment'] = ['wrong_pk']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        response = scoreset_create_view(request)

        self.assertEqual(ScoreSet.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_scoreset_created_with_current_user_as_admin(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertTrue(user_is_admin_for_instance(self.user, scs))

    def test_scoreset_published_sends_email_to_admin(self):
        self.user.is_superuser = True
        self.user.email = "admin@admin.com"
        self.user.save()

        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]
        data['publish'] = ['publish']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertFalse(scs.private)
        self.assertEqual(len(mail.outbox), 1)

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
            response = scoreset_create_view(request)

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
            response = scoreset_create_view(request)

            self.assertContains(response, instance.identifier)

    def test_failed_submission_adds_keywords_to_context(self):
        data = self.post_data.copy()
        kw = KeywordFactory()
        data['keywords'] = ['protein', kw.text]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        response = scoreset_create_view(request)

        self.assertContains(response, 'protein')
        self.assertContains(response, kw.text)

    def test_publish_propagates_modified_by(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]
        data['publish'] = ['publish']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertEqual(scs.modified_by, self.user)
        self.assertEqual(scs.parent.modified_by, self.user)
        self.assertEqual(scs.parent.parent.modified_by, self.user)

    def test_publish_propagates_private_as_false(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]
        data['publish'] = ['publish']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertFalse(scs.private)
        self.assertFalse(scs.parent.private)
        self.assertFalse(scs.parent.parent.private)

    def test_publish_does_not_propagate_created_by(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]
        data['publish'] = ['publish']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertEqual(scs.created_by, self.user)
        self.assertNotEqual(scs.parent.created_by, scs.created_by)
        self.assertNotEqual(scs.parent.parent.created_by, scs.created_by)

    def test_not_publishing_does_not_propagate_user_fields(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_admin(self.user, exp1)
        data['experiment'] = [exp1.pk]

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertEqual(scs.created_by, self.user)
        self.assertNotEqual(scs.parent.created_by, scs.created_by)
        self.assertNotEqual(scs.parent.parent.created_by, scs.created_by)

        self.assertEqual(scs.modified_by, self.user)
        self.assertNotEqual(scs.parent.modified_by, scs.modified_by)
        self.assertNotEqual(scs.parent.parent.modified_by, scs.modified_by)

    def test_does_not_add_user_as_admin_to_selected_parent(self):
        data = self.post_data.copy()
        exp1 = ExperimentFactory()
        assign_user_as_instance_editor(self.user, exp1)
        data['experiment'] = [exp1.pk]
        data['publish'] = ['publish']

        request = self.factory.post(path=self.path, data=data)
        request.user = self.user
        request.FILES.update(self.files)
        _ = scoreset_create_view(request)

        scs = ScoreSet.objects.all()[0]
        self.assertFalse(user_is_admin_for_instance(self.user, scs.parent))
        self.assertFalse(user_is_admin_for_instance(
            self.user, scs.parent.parent))

    def test_ajax_submission_returns_json_response(self):
        data = self.post_data.copy()
        data['abstractText'] = "# Hello world"
        data['methodText'] = "## foo bar"
        data['markdown'] = [True]

        request = self.factory.get(
            path=self.path, data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user
        response = scoreset_create_view(request)
        self.assertContains(response, 'pandoc')

    def test_came_from_experiment_locks_experiment_choice(self):
        exp1 = ExperimentFactory()
        exp2 = ExperimentFactory()
        assign_user_as_instance_editor(self.user, exp1)
        assign_user_as_instance_editor(self.user, exp2)

        request = self.factory.get(path=self.path)
        request.user = self.user
        request.FILES.update(self.files)
        response = scoreset_create_view(request, experiment_urn=exp1.urn)
        self.assertContains(response, exp1.urn)
        self.assertNotContains(response, exp2.urn)
