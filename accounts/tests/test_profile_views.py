from django.core import mail
from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser

from dataset.tests.utility import make_score_count_files
import dataset.constants as constants
from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from dataset.factories import (
    ScoreSetFactory, ExperimentFactory, ExperimentSetFactory
)

from genome.factories import (
    ReferenceGenomeFactory, IntervalFactory
)

from ..factories import UserFactory, AnonymousUserFactory, ProfileFactory
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer,
    remove_user_as_instance_admin,
    remove_user_as_instance_viewer,
    instances_for_user_with_group_permission,
    user_is_admin_for_instance,
    user_is_viewer_for_instance
)
from ..views import (
    manage_instance,
    edit_instance,
    profile_view,
    view_instance,
    get_class_from_urn
)


class TestProfileHomeView(TestCase):
    """
    Test the home view loads the correct template and requires a login.
    """
    def setUp(self):
        self.path = reverse_lazy("accounts:profile")
        self.factory = RequestFactory()
        self.template = 'accounts/profile_home.html'
        self.alice = UserFactory(username="alice")

    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)


class TestProfileManageInstanceView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.alice = UserFactory(username="alice", password="secret")
        self.bob = UserFactory(username="bob", password="secret")
        self.client.logout()

    def test_requires_login(self):
        obj = ExperimentSetFactory()
        request = self.factory.get(
            '/profile/manage/{}/'.format(obj.urn))
        request.user = AnonymousUser()
        response = view_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_403_if_user_does_not_have_manage_permissions(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get(
            '/profile/manage/{}/'.format(obj.urn))
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_404_if_klass_cannot_be_inferred_from_urn(self):
        request = self.factory.get('/profile/manage/NOT_ACCESSION/')
        request.user = self.alice
        response = manage_instance(request, urn='NOT_ACCESSION')
        self.assertEqual(response.status_code, 404)

    def test_404_if_instance_not_found(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_viewer(self.alice, obj)
        obj.delete()
        request = self.factory.get(
            '/profile/manage/{}/'.format(obj.urn))
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 404)

    def test_removes_existing_admin(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "administrators[]": [self.bob.pk],
                "administrator_management-users": [self.bob.pk]
            }
        )
        request.user = self.alice
        manage_instance(request, urn=obj.urn)
        self.assertFalse(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_admin_for_instance(self.bob, obj))

    def test_appends_new_admin(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "viewers[]": [self.bob.pk],
                "viewer_management-users": [self.bob.pk]
            }
        )
        request.user = self.alice
        manage_instance(request, urn=obj.urn)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_viewer_for_instance(self.bob, obj))

    def test_redirects_to_manage_page_valid_submission(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "administrators[]": [self.alice.pk, self.bob.pk],
                "administrator_management-users": [self.alice.pk, self.bob.pk]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_returns_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "administrators[]": [10000],
                "administrator_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)

    def test_returns_viewer_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "viewers[]": [10000],
                "viewer_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)


class TestProfileEditInstanceView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.ref = ReferenceGenomeFactory()
        self.base_post_data = {
            'keywords': [''],
            'sra_ids': [''],
            'doi_ids': [''],
            'short_description': ['a thing'],
            'title': ['title'],
            'pubmed_ids': [''],
            'start': [1],
            'end': [2],
            'chromosome': ['chrX'],
            'strand': ['F'],
            'genome': [self.ref.pk],
            'is_primary': True,
            'wt_sequence': 'atcg',
            'name': 'BRCA1',
            'submit': ['submit'],
            'publish': ['']
        }
        self.user = UserFactory()
        self.username = self.user.username
        self.unencrypted_password = 'secret_key'
        self.user.set_password(self.unencrypted_password)
        self.user.save()
        self.client.login(
            username=self.username, password=self.unencrypted_password)

    def make_scores_test_data(self, scores_data=None, counts_data=None):
        data = self.base_post_data.copy()
        s_file, c_file = make_score_count_files(scores_data, counts_data)
        files = {constants.variant_score_data: s_file}
        if c_file is not None:
            files[constants.variant_count_data] = c_file
        return data, files

    def test_404_object_not_found(self):
        obj = ExperimentFactory()
        urn = obj.urn
        assign_user_as_instance_viewer(self.user, obj)
        request = self.factory.get('/profile/edit/{}/'.format(urn))
        request.user = self.user
        obj.delete()

        response = edit_instance(request, urn=urn)
        self.assertEqual(response.status_code, 404)

    def test_publish_button_sends_admin_emails(self):
        user = UserFactory()
        user.is_superuser = True
        user.email = "admin@admin.com"
        user.save()
        
        obj = ScoreSetFactory()
        interval = IntervalFactory()
        interval.reference_map.target.scoreset = obj
        interval.reference_map.target.save()

        assign_user_as_instance_admin(self.user, obj)
        assign_user_as_instance_admin(self.user, obj.parent)
        data, _ = self.make_scores_test_data()
        data['publish'] = ['publish']
        data['experiment'] = [obj.parent.pk]

        path = '/profile/edit/{}/'.format(obj.urn)
        request = self.factory.post(path=path, data=data)
        request.user = self.user
        _ = edit_instance(request, obj.urn)
        self.assertEqual(len(mail.outbox), 1)

    def test_publishing_sets_child_and_parents_to_public(self):
        obj = ScoreSetFactory()
        interval = IntervalFactory()
        interval.reference_map.target.scoreset = obj
        interval.reference_map.target.save()

        assign_user_as_instance_admin(self.user, obj)
        assign_user_as_instance_admin(self.user, obj.parent)

        data, _ = self.make_scores_test_data()
        data['experiment'] = [obj.parent.pk]
        data['publish'] = ['publish']

        path = '/profile/edit/{}/'.format(obj.urn)
        request = self.factory.post(path=path, data=data)
        request.user = self.user
        _ = edit_instance(request, obj.urn)

        obj = ScoreSet.objects.get(urn=obj.urn)
        self.assertFalse(obj.private)
        self.assertFalse(obj.parent.private)
        self.assertFalse(obj.parent.parent.private)

    def test_publishing_propagates_modified_by(self):
        obj = ScoreSetFactory()
        interval = IntervalFactory()
        interval.reference_map.target.scoreset = obj
        interval.reference_map.target.save()

        ref = ReferenceGenomeFactory()

        obj.propagate_set_value('private', True)
        obj.save(save_parents=True)

        assign_user_as_instance_admin(self.user, obj)
        assign_user_as_instance_admin(self.user, obj.parent)

        data, _ = self.make_scores_test_data()
        data['experiment'] = [obj.parent.pk]
        data['publish'] = ['publish']
        data.update(**{
            'start': [1],
            'end': [2],
            'chromosome': ['chrX'],
            'strand': ['F'],
            'genome': [ref.pk],
            'is_primary': True,
            'wt_sequence': 'atcg',
            'name': 'BRCA1',
        })

        path = '/profile/edit/{}/'.format(obj.urn)
        request = self.factory.post(path=path, data=data)
        request.user = self.user
        _ = edit_instance(request, obj.urn)

        obj = ScoreSet.objects.get(urn=obj.urn)
        self.assertEqual(obj.modified_by, self.user)
        self.assertEqual(obj.experiment.modified_by, self.user)
        self.assertEqual(obj.experiment.experimentset.modified_by, self.user)

    def test_requires_login(self):
        self.client.logout()
        obj = ExperimentFactory()
        response = self.client.get(
            '/profile/edit/{}/'.format(obj.urn))
        self.assertEqual(response.status_code, 302)

    def test_can_defer_instance_type_from_urn(self):
        urn = ExperimentFactory().urn
        self.assertEqual(get_class_from_urn(urn), Experiment)

        urn = ExperimentSetFactory().urn
        self.assertEqual(get_class_from_urn(urn), ExperimentSet)

        urn = ScoreSetFactory().urn
        self.assertEqual(get_class_from_urn(urn), ScoreSet)

        urn = "urn:mavedb:00000a"
        self.assertEqual(get_class_from_urn(urn), None)

    def test_404_edit_an_ExperimentSetFactory(self):
        obj = ExperimentSetFactory()
        request = self.factory.get(
            '/profile/edit/{}/'.format(obj.urn))
        request.user = self.user
        response = edit_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 404)

    def test_published_scoreset_instance_returns_edit_only_mode_form(self):
        obj = ScoreSetFactory()
        obj.private = False
        obj.save()
        assign_user_as_instance_admin(self.user, obj)
        request = self.factory.get('accounts/profile/edit/{}/'.format(obj.urn))
        request.user = self.user
        response = edit_instance(request, urn=obj.urn)
        self.assertNotContains(response, 'Score data')
        self.assertNotContains(response, 'Count data')

    def test_published_experiment_instance_returns_edit_only_mode_form(self):
        obj = ExperimentFactory()
        obj.private = False
        obj.save()
        assign_user_as_instance_admin(self.user, obj)
        request = self.factory.get(
            '/profile/edit/{}/'.format(obj.urn))
        request.user = self.user
        response = edit_instance(request, urn=obj.urn)
        self.assertNotContains(response, 'Target')

    def test_ajax_submission_returns_json_response(self):
        data = dict()
        data['abstractText'] = "# Hello world"
        data['methodText'] = "## foo bar"
        data['markdown'] = [True]

        obj = ScoreSetFactory()
        interval = IntervalFactory()
        interval.reference_map.target.scoreset = obj
        interval.reference_map.target.save()

        assign_user_as_instance_admin(self.user, obj)
        path = '/profile/edit/{}/'.format(obj.urn)
        request = self.factory.get(
            path=path, data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        request.user = self.user
        response = edit_instance(request, urn=obj.urn)
        self.assertContains(response, 'pandoc')


class TestProfileViewInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:view_instance")
        self.factory = RequestFactory()
        self.alice = UserFactory(username="alice")
        self.bob = UserFactory(username="bob")

    def test_requires_login(self):
        obj = ExperimentSetFactory()
        request = self.factory.get('/profile/view/{}/'.format(obj.urn))
        request.user = AnonymousUser()
        response = view_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_403_if_no_permissions(self):
        obj = ExperimentSetFactory()
        request = self.factory.get('/profile/view/{}/'.format(obj.urn))
        request.user = self.alice
        response = view_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_404_if_obj_not_found(self):
        obj = ExperimentSetFactory()
        urn = obj.urn
        assign_user_as_instance_viewer(self.alice, obj)
        obj.delete()

        request = self.factory.get('/profile/view/{}/'.format(urn))
        request.user = self.alice
        response = view_instance(request, urn=urn)
        self.assertEqual(response.status_code, 404)
