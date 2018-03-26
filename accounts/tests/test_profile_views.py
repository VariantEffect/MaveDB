from django.core import mail
from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from ..views import (
    manage_instance,
    edit_instance,
    profile_view,
    view_instance,
    get_class_from_urn
)

import dataset.constants as constants
from dataset.models import ExperimentSet, Experiment, ScoreSet
from scoreset.tests.utility import make_score_count_files

from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer,
    remove_user_as_instance_admin,
    remove_user_as_instance_viewer,
    instances_for_user_with_group_permission,
    user_is_admin_for_instance,
    user_is_viewer_for_instance
)


User = get_user_model()


def experimentset():
    return ExperimentSet.objects.create()


def experiment():
    return Experiment.objects.create(target="test", wt_sequence="AT")


def scoreset():
    return ScoreSet.objects.create(
        experiment=Experiment.objects.create(
            target="test", wt_sequence="AT"
        )
    )


class TestProfileHomeView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:profile")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")

    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)


class TestProfileManageInstanceView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice", password="secret")
        self.bob = User.objects.create(username="bob", password="secret")
        self.client.logout()

    def test_requires_login(self):
        obj = ExperimentSet.objects.create()
        request = self.factory.get(
            '/accounts/profile/manage/{}/'.format(obj.urn))
        request.user = AnonymousUser()
        response = view_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_403_if_user_does_not_have_manage_permissions(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get(
            '/accounts/profile/manage/{}/'.format(obj.urn))
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_404_if_klass_cannot_be_inferred_from_urn(self):
        request = self.factory.get('/accounts/profile/manage/NOT_ACCESSION/')
        request.user = self.alice
        response = manage_instance(request, urn='NOT_ACCESSION')
        self.assertEqual(response.status_code, 404)

    def test_404_if_instance_not_found(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_viewer(self.alice, obj)
        obj.delete()
        request = self.factory.get(
            '/accounts/profile/manage/{}/'.format(obj.urn))
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 404)

    def test_removes_existing_admin(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.urn),
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
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.urn),
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
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.urn),
            data={
                "administrators[]": [self.alice.pk, self.bob.pk],
                "administrator_management-users": [self.alice.pk, self.bob.pk]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_returns_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.urn),
            data={
                "administrators[]": [10000],
                "administrator_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)

    def test_returns_viewer_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSet.objects.create()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.factory.post(
            path='/accounts/profile/manage/{}/'.format(obj.urn),
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
        self.path = reverse_lazy("accounts:edit_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.alice.set_password("secret_key")
        self.alice.save()
        self.bob = User.objects.create(username="bob")
        self.base_post_data = {
            'keywords': [''],
            'sra_ids': [''],
            'doi_ids': [''],
            'pmid_ids': [''],
            'submit': ['submit'],
            'publish': ['']
        }

    def make_scores_test_data(self, scores_data=None, counts_data=None):
        data = self.base_post_data.copy()
        s_file, c_file = make_score_count_files(scores_data, counts_data)
        files = {constants.variant_score_data: s_file}
        if c_file is not None:
            files[constants.variant_count_data] = c_file
        return data, files

    def test_404_object_not_found(self):
        obj = experiment()
        urn = obj.urn
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.factory.get('/accounts/profile/edit/{}/'.format(urn))
        request.user = self.alice
        obj.delete()

        response = edit_instance(request, urn=urn)
        self.assertEqual(response.status_code, 404)

    def test_publish_button_sends_admin_emails(self):
        admin = User.objects.create(username="admin", email="admin@admin.com")
        admin.is_superuser = True
        admin.save()

        obj = scoreset()
        exp = Experiment.objects.create(wt_sequence='atcg', target='brca1')
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_admin(self.alice, exp)

        data, _ = self.make_scores_test_data()
        score_file, count_file = make_score_count_files()
        data['score_data'] = score_file
        data['count_data'] = count_file
        data['experiment'] = exp.pk
        data['publish'] = ['publish']
        path = '/accounts/profile/edit/{}/'.format(obj.urn)
        self.client.login(username="alice", password="secret_key")
        self.client.post(path=path, data=data)

        obj.refresh_from_db()
        self.assertEqual(len(mail.outbox), 1)

    def test_publishing_sets_child_and_parents_to_public(self):
        admin = User.objects.create(username="admin", email="admin@admin.com")
        admin.is_superuser = True
        admin.save()

        obj = scoreset()
        exp = Experiment.objects.create(wt_sequence='atcg', target='brca1')
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_admin(self.alice, exp)

        data, _ = self.make_scores_test_data()
        score_file, count_file = make_score_count_files()
        data['score_data'] = score_file
        data['count_data'] = count_file
        data['experiment'] = exp.pk
        data['publish'] = ['publish']
        path = '/accounts/profile/edit/{}/'.format(obj.urn)
        self.client.login(username="alice", password="secret_key")
        self.client.post(path=path, data=data)

        obj.refresh_from_db()
        self.assertFalse(obj.private)
        self.assertFalse(obj.experiment.private)
        self.assertFalse(obj.experiment.experimentset.private)
#
#     def test_requires_login(self):
#         obj = experiment()
#         response = self.client.get(
#             '/accounts/profile/edit/{}/'.format(obj.urn)
#         )
#         self.assertEqual(response.status_code, 302)
#
#     def test_can_defer_instance_type_from_urn(self):
#         urn = experiment().urn
#         self.assertEqual(get_class_from_urn(urn), Experiment)
#
#         urn = experimentset().urn
#         self.assertEqual(get_class_from_urn(urn), ExperimentSet)
#
#         urn = scoreset().urn
#         self.assertEqual(get_class_from_urn(urn), ScoreSet)
#
#         urn = "exp12012.1A"
#         self.assertEqual(get_class_from_urn(urn), None)
#
#     def test_404_edit_an_experimentset(self):
#         obj = experimentset()
#         request = self.factory.get(
#             '/accounts/profile/edit/{}/'.format(obj.urn)
#         )
#         request.user = self.alice
#         response = edit_instance(request, urn=obj.urn)
#         self.assertEqual(response.status_code, 404)
#
#     def test_published_scoreset_instance_returns_edit_only_mode_form(self):
#         obj = scoreset()
#         obj.private = False
#         obj.save()
#         assign_user_as_instance_admin(self.alice, obj)
#         request = self.factory.get(
#             '/accounts/profile/edit/{}/'.format(obj.urn)
#         )
#         request.user = self.alice
#         response = edit_instance(request, urn=obj.urn)
#         self.assertNotContains(response, 'Score data')
#         self.assertNotContains(response, 'Count data')
#
#     def test_published_experiment_instance_returns_edit_only_mode_form(self):
#         obj = experiment()
#         obj.private = False
#         obj.save()
#         assign_user_as_instance_admin(self.alice, obj)
#         request = self.factory.get(
#             '/accounts/profile/edit/{}/'.format(obj.urn)
#         )
#         request.user = self.alice
#         response = edit_instance(request, urn=obj.urn)
#         self.assertNotContains(response, 'Target')


class TestProfileViewInstanceView(TestCase):

    def setUp(self):
        self.path = reverse_lazy("accounts:view_instance")
        self.factory = RequestFactory()
        self.alice = User.objects.create(username="alice")
        self.bob = User.objects.create(username="bob")

    def test_requires_login(self):
        obj = ExperimentSet.objects.create()
        request = self.factory.get('/accounts/profile/view/{}/'.format(obj.urn))
        request.user = AnonymousUser()
        response = view_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_403_if_no_permissions(self):
        obj = ExperimentSet.objects.create()
        request = self.factory.get('/accounts/profile/view/{}/'.format(obj.urn))
        request.user = self.alice
        response = view_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 403)

    def test_404_if_obj_not_found(self):
        obj = ExperimentSet.objects.create()
        urn = obj.urn
        assign_user_as_instance_viewer(self.alice, obj)
        obj.delete()

        request = self.factory.get('/accounts/profile/view/{}/'.format(urn))
        request.user = self.alice
        response = view_instance(request, urn=urn)
        self.assertEqual(response.status_code, 404)
