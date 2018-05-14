from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.core import mail
from django.core.exceptions import PermissionDenied

from dataset import constants
from dataset import models as dataset_models
from dataset.factories import ExperimentSetFactory, ScoreSetFactory

from core.utilities.tests import TestMessageMixin

from ..factories import UserFactory
from ..permissions import (
    GroupTypes,
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer,
    assign_user_as_instance_editor,
    user_is_admin_for_instance,
    user_is_viewer_for_instance,
    user_is_editor_for_instance,
)

from ..views import manage_instance, profile_view, profile_settings


class TestProfileSettings(TestCase, TestMessageMixin):
    """
    Test the settings view forms.
    """
    def setUp(self):
        self.path = reverse_lazy("accounts:profile_settings")
        self.factory = RequestFactory()
        self.template = 'accounts/profile_settings.html'
        self.alice = UserFactory(username="alice")

    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)

    def test_can_set_email(self):
        user = UserFactory()
        request = self.create_request(
            method='post',
            path='/profile/',
            data={'email': 'email@email.com'}
        )
        request.user = user
        response = profile_settings(request)
        self.assertContains(response, 'email@email.com')

    def test_cannot_set_invalid_email(self):
        user = UserFactory()
        request = self.create_request(
            method='post',
            path='/profile/',
            data={'email': 'not an email.com'}
        )
        request.user = user
        response = profile_settings(request)
        self.assertContains(response, 'There were errors')

    def test_setting_email_emails_user(self):
        user = UserFactory()
        request = self.create_request(
            method='post',
            path='/profile/',
            data={'email': 'email@email.com'}
        )
        request.user = user
        _ = profile_settings(request)
        self.assertEqual(len(mail.outbox), 1)

    def test_users_email_appears_in_profile(self):
        user = UserFactory()
        request = self.create_request(
            method='get',
            path='/profile/',
        )
        request.user = user
        response = profile_settings(request)
        self.assertContains(response, user.profile.email)


class TestProfileHomeView(TestCase, TestMessageMixin):
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

    def test_can_delete_private_entry(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        assign_user_as_instance_admin(user, instance)
        request = self.create_request(
            method='post',
            data={"delete": instance.urn},
            path='/profile/',
        )
        request.user = user
        response = profile_view(request)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 0)

    def test_cannot_delete_public_entry(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance.publish()
        instance.save(save_parents=True)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        assign_user_as_instance_admin(user, instance)
        request = self.create_request(
            method='post',
            data={"delete": instance.urn},
            path='/profile/',
        )
        request.user = user
        response = profile_view(request)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        self.assertContains(response, "is public and cannot be deleted.")

    def test_returns_error_message_if_urn_does_not_exist(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        assign_user_as_instance_admin(user, instance)
        request = self.create_request(
            method='post',
            data={"delete": instance.urn},
            path='/profile/',
        )
        request.user = user
        instance.delete()
        response = profile_view(request)
        self.assertContains(response, "already been deleted.")

    def test_cannot_delete_if_not_an_admin(self):
        editor = UserFactory()
        viewer = UserFactory()
        instance = ScoreSetFactory()
        assign_user_as_instance_editor(editor, instance)
        assign_user_as_instance_viewer(viewer, instance)
        request = self.create_request(
            method='post',
            data={"delete": instance.urn},
            path='/profile/',
        )
        request.user = editor
        response = profile_view(request)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        self.assertContains(response, "You must be an administrator")

        request = self.create_request(
            method='post',
            data={"delete": instance.urn},
            path='/profile/',
        )
        request.user = viewer
        response = profile_view(request)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        self.assertContains(response, "You must be an administrator")

    def test_can_delete_experimentset_if_it_has_children(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance.publish()
        assign_user_as_instance_admin(user, instance.experiment.experimentset)
        request = self.create_request(
            method='post',
            data={"delete": instance.experiment.experimentset.urn},
            path='/profile/',
        )
        request.user = user
        response = profile_view(request)
        self.assertContains(response, "Child entries must be deleted")
        self.assertEqual(dataset_models.experimentset.ExperimentSet.objects.count(), 1)
        self.assertEqual(dataset_models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)

    def test_can_delete_experiment_if_it_has_children(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance.publish()
        assign_user_as_instance_admin(user, instance.experiment)
        request = self.create_request(
            method='post',
            data={"delete": instance.experiment.urn},
            path='/profile/',
        )
        request.user = user
        response = profile_view(request)
        self.assertContains(response, "Child entries must be deleted")
        self.assertEqual(dataset_models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)

    def test_cannot_delete_entry_being_processed(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance.publish()
        assign_user_as_instance_admin(user, instance)
        request = self.create_request(
            method='post',
            data={"delete": instance.urn},
            path='/profile/',
        )
        request.user = user
        instance.processing_state = constants.processing
        instance.save()
        response = profile_view(request)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        self.assertContains(response, "being processed cannot be deleted.")


class TestProfileManageInstanceView(TestCase, TestMessageMixin):
    def setUp(self):
        self.factory = RequestFactory()
        self.alice = UserFactory(username="alice", password="secret")
        self.bob = UserFactory(username="bob", password="secret")
        self.raw_password = 'secret'
        self.client.logout()

    def login(self, user):
        return self.client.login(
            username=user.username, password=self.raw_password)

    def test_requires_login(self):
        obj = ExperimentSetFactory()
        request = self.create_request(
            method='get', path='/profile/manage/{}/'.format(obj.urn))
        request.user = AnonymousUser()
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_403_if_user_does_not_have_manage_permissions(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_viewer(self.alice, obj)
        request = self.create_request(
            method='get', path='/profile/manage/{}/'.format(obj.urn))
        request.user = self.alice
        with self.assertRaises(PermissionDenied):
            manage_instance(request, urn=obj.urn)

    def test_404_if_klass_cannot_be_inferred_from_urn(self):
        request = self.create_request(
            method='get', path='/profile/manage/NOT_ACCESSION/')
        request.user = self.alice
        with self.assertRaises(Http404):
            manage_instance(request, urn='NOT_ACCESSION')

    def test_404_if_instance_not_found(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_viewer(self.alice, obj)
        obj.delete()
        request = self.create_request(
            method='get', path='/profile/manage/{}/'.format(obj.urn))
        request.user = self.alice
        with self.assertRaises(Http404):
            manage_instance(request, urn=obj.urn)

    # --- Removing
    def test_removes_existing_admin(self):
        group = GroupTypes.ADMIN
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [self.bob.pk]
        }

        self.client.post(path=path, data=data)
        self.assertFalse(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_admin_for_instance(self.bob, obj))
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(self.alice.first_name, mail.outbox[0].body)
        self.assertIn(self.bob.first_name, mail.outbox[1].body)
        self.assertIn('removed', mail.outbox[0].body)
        self.assertIn('added', mail.outbox[1].body)

    def test_removes_existing_editor(self):
        group = GroupTypes.EDITOR
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_editor(self.bob, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): []
        }

        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertFalse(user_is_editor_for_instance(self.bob, obj))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('removed', mail.outbox[0].body)

    def test_removes_existing_viewer(self):
        group = GroupTypes.VIEWER
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_viewer(self.bob, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): []
        }

        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertFalse(user_is_viewer_for_instance(self.bob, obj))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('removed', mail.outbox[0].body)

    # --- Re-assign
    def test_error_reassign_only_admin(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        group = GroupTypes.EDITOR
        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [self.alice.pk]
        }
        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertEqual(len(mail.outbox), 0)

        group = GroupTypes.VIEWER
        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [self.alice.pk]
        }
        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertEqual(len(mail.outbox), 0)

    def test_reassign_removes_from_existing_group(self):
        group = GroupTypes.EDITOR
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_viewer(self.bob, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [self.bob.pk]
        }

        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertFalse(user_is_viewer_for_instance(self.bob, obj))
        self.assertTrue(user_is_editor_for_instance(self.bob, obj))
        # Removal email and addition email should be sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('re-assigned', mail.outbox[0].body)

    # --- Adding
    def test_appends_new_admin(self):
        group = GroupTypes.ADMIN
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [self.alice.pk, self.bob.pk]
        }

        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_admin_for_instance(self.bob, obj))
        self.assertEqual(len(mail.outbox), 1)  # only sent to new additions
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('added', mail.outbox[0].body)

    def test_appends_new_viewer(self):
        group = GroupTypes.VIEWER
        userc = UserFactory()
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_viewer(userc, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [userc.pk, self.bob.pk]
        }

        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_viewer_for_instance(self.bob, obj))
        self.assertTrue(user_is_viewer_for_instance(userc, obj))

        self.assertEqual(len(mail.outbox), 1)  # only sent to new additions
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('added', mail.outbox[0].body)

    def test_appends_new_editor(self):
        group = GroupTypes.EDITOR
        userc = UserFactory()
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        assign_user_as_instance_editor(userc, obj)

        success = self.login(self.alice)
        self.assertTrue(success)

        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [userc.pk, self.bob.pk]
        }

        self.client.post(path=path, data=data)
        self.assertTrue(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_editor_for_instance(self.bob, obj))
        self.assertTrue(user_is_editor_for_instance(userc, obj))

        self.assertEqual(len(mail.outbox), 1)  # only sent to new additions
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('added', mail.outbox[0].body)

    # --- Redirects
    def test_redirects_valid_submission(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.create_request(
            method='post',
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "administrator[]": [''],
                "administrator_management-users": [self.alice.pk, self.bob.pk]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)

    def test_returns_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.create_request(
            method='post',
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "administrator[]": [10000],
                "administrator_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)

    def test_returns_viewer_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.create_request(
            method='post',
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "viewer[]": [10000],
                "viewer_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)

    def test_returns_editor_admin_form_when_inputting_invalid_data(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.create_request(
            method='post',
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "editor[]": [10000],
                "editor_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)
