from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory, mock
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.shortcuts import reverse

from dataset import constants
from dataset.utilities import delete_instance, publish_dataset
from dataset import models as dataset_models
from dataset.tasks import publish_scoreset
from dataset.models.scoreset import ScoreSet
from dataset.factories import (
    ExperimentSetFactory, ScoreSetFactory, ScoreSetWithTargetFactory,
    ExperimentFactory
)
from variant.factories import VariantFactory

from core.utilities.tests import TestMessageMixin
from core.models import FailedTask
from core.tasks import send_mail

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

from ..views import manage_instance, profile_view, profile_settings, ContributorSummary


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
        self.assertEqual(response.status_code, 302)

    def test_cannot_set_invalid_email(self):
        user = UserFactory()
        request = self.create_request(
            method='post',
            path='/profile/',
            data={'email': 'not an email.com'}
        )
        request.user = user
        response = profile_settings(request)
        self.assertContains(response, 'valid email')
    
    @mock.patch("core.tasks.send_mail.apply_async")
    def test_setting_email_emails_user(self, patch):
        user = UserFactory()
        request = self.create_request(
            method='post',
            path='/profile/',
            data={'email': 'email@email.com'}
        )
        request.user = user
        _ = profile_settings(request)
        patch.assert_called()

    def test_users_email_appears_in_profile(self):
        user = UserFactory()
        request = self.create_request(
            method='get',
            path='/profile/',
        )
        request.user = user
        response = profile_settings(request)
        self.assertContains(response, user.profile.email)


class TestProfileDeleteInstance(TestCase, TestMessageMixin):
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
        instance = publish_dataset(instance)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)
        instance.add_administrators(user)
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

    def test_cannot_delete_experimentset_if_it_has_children(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance = publish_dataset(instance)
        assign_user_as_instance_admin(user, instance.experiment.experimentset)
        request = self.create_request(
            method='post',
            data={"delete": instance.experiment.experimentset.urn},
            path='/profile/',
        )
        request.user = user
        response = profile_view(request)
        self.assertContains(response, "Child Experiments must be deleted")
        self.assertEqual(dataset_models.experimentset.ExperimentSet.objects.count(), 1)
        self.assertEqual(dataset_models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)

    def test_cannot_delete_experiment_if_it_has_children(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance = publish_dataset(instance)
        assign_user_as_instance_admin(user, instance.experiment)
        request = self.create_request(
            method='post',
            data={"delete": instance.experiment.urn},
            path='/profile/',
        )
        request.user = user
        response = profile_view(request)
        self.assertContains(response, "Child Score Sets must be deleted")
        self.assertEqual(dataset_models.experiment.Experiment.objects.count(), 1)
        self.assertEqual(dataset_models.scoreset.ScoreSet.objects.count(), 1)

    def test_cannot_delete_entry_being_processed(self):
        user = UserFactory()
        instance = ScoreSetFactory()
        instance = publish_dataset(instance)
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
        self.assertContains(response, "currently being processed.")


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
        
    def test_redirects_to_summary_when_user_removed_as_admin(self):
        group = GroupTypes.ADMIN
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
    
        path = '/profile/manage/{}/'.format(obj.urn)
        data = {
            "{}[]".format(group): [''],
            "{}_management-users".format(group): [self.bob.pk]
        }
        request = self.create_request('post', path=path, data=data)
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed(response, 'contributor_summary.html')
        self.assertFalse(user_is_admin_for_instance(self.alice, obj))
        self.assertTrue(user_is_admin_for_instance(self.bob, obj))

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
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_removes_existing_admin(self, patch):
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
        
        self.assertEqual(patch.call_count, 2)
        send_mail.apply(**patch.call_args_list[0][1])
        send_mail.apply(**patch.call_args_list[1][1])
        
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(self.alice.first_name, mail.outbox[0].body)
        self.assertIn(self.bob.first_name, mail.outbox[1].body)
        self.assertIn('removed', mail.outbox[0].body)
        self.assertIn('added', mail.outbox[1].body)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_removes_existing_editor(self, patch):
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

        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('removed', mail.outbox[0].body)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_removes_existing_viewer(self, patch):
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
        
        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
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

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_reassign_removes_from_existing_group(self, patch):
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
        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('re-assigned', mail.outbox[0].body)

    # --- Adding
    @mock.patch('core.tasks.send_mail.apply_async')
    def test_appends_new_admin(self, patch):
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
        
        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
        self.assertEqual(len(mail.outbox), 1)  # only sent to new additions
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('added', mail.outbox[0].body)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_appends_new_viewer(self, patch):
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
    
        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
        self.assertEqual(len(mail.outbox), 1)  # only sent to new additions
        self.assertIn(self.bob.first_name, mail.outbox[0].body)
        self.assertIn('added', mail.outbox[0].body)

    @mock.patch('core.tasks.send_mail.apply_async')
    def test_appends_new_editor(self, patch):
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

        patch.assert_called()
        send_mail.apply(**patch.call_args[1])
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



class TestPublish(TestCase, TestMessageMixin):
    def setUp(self):
        self.user = UserFactory()
        self.scoreset = ScoreSetWithTargetFactory()
        self.path = '/profile/'
        self.factory = RequestFactory()
        self.post_data = {'publish': [self.scoreset.urn]}
        for i in range(3):
            VariantFactory(scoreset=self.scoreset)
            
    def make_request(self, user=None):
        data = self.post_data.copy()
        self.scoreset.add_administrators(self.user if user is None else user)
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user if user is None else user
        return request
    
    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publishing_updates_states_success(self, publish_mock):
        profile_view(self.make_request())
        self.assertEqual(
            ScoreSet.objects.first().processing_state, constants.processing)
        publish_mock.assert_called_once()
        publish_scoreset.apply(**publish_mock.call_args[1])
        self.assertEqual(
            ScoreSet.objects.first().processing_state, constants.success)
        
    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publishing_updates_states_fail(self, publish_mock):
        profile_view(self.make_request())
        self.assertEqual(
            ScoreSet.objects.first().processing_state, constants.processing)
        publish_mock.assert_called_once()

        publish_scoreset.scoreset = self.scoreset
        publish_scoreset.base_url = ""
        publish_scoreset.user = self.user
        publish_scoreset.urn = self.scoreset.urn
        publish_scoreset.on_failure(
            exc=None, task_id=1, args=(), einfo=None, kwargs={})
        self.assertEqual(
            ScoreSet.objects.first().processing_state, constants.failed)
        
    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publishing_sets_child_and_parents_to_public(self, publish_mock):
        self.assertTrue(self.scoreset.private)
        self.assertTrue(self.scoreset.parent.private)
        self.assertTrue(self.scoreset.parent.parent.private)
        
        profile_view(self.make_request())
        publish_mock.assert_called_once()
        publish_scoreset.apply(**publish_mock.call_args[1])

        obj = ScoreSet.objects.first()
        self.assertFalse(obj.private)
        self.assertFalse(obj.parent.private)
        self.assertFalse(obj.parent.parent.private)

    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publishing_propagates_modified_by(self, publish_mock):
        self.assertIsNone(self.scoreset.modified_by)
        self.assertIsNone(self.scoreset.parent.modified_by)
        self.assertIsNone(self.scoreset.parent.parent.modified_by)
        
        profile_view(self.make_request())
        publish_mock.assert_called_once()
        publish_scoreset.apply(**publish_mock.call_args[1])

        obj = ScoreSet.objects.first()
        self.assertEqual(obj.modified_by, self.user)
        self.assertEqual(obj.experiment.modified_by, self.user)
        self.assertEqual(obj.experiment.experimentset.modified_by, self.user)

    @mock.patch('core.tasks.send_mail.apply_async')
    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publish_emails_admins_on_success(self, publish_mock, email_mock):
        user = UserFactory(is_superuser=True)
        profile_view(self.make_request())
        publish_mock.assert_called_once()
        publish_scoreset.apply(**publish_mock.call_args[1])
        
        self.assertEqual(
            email_mock.call_args_list[1][1]['kwargs']['recipient_list'],
            [user.profile.email]
        )
        

    @mock.patch('core.tasks.send_mail.apply_async')
    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publish_emails_user_on_success(self, publish_mock, email_mock):
        profile_view(self.make_request())
        publish_mock.assert_called_once()
        
        publish_scoreset.apply(**publish_mock.call_args[1])
        email_mock.assert_called()
        self.assertEqual(
            email_mock.call_args[1]['kwargs']['recipient_list'],
            [self.user.email]
        )
        self.assertIn(
            'successfully processed',
            email_mock.call_args[1]['kwargs']['message']
        )
        self.scoreset.refresh_from_db()
        self.assertIn(
            self.scoreset.get_url(),
            email_mock.call_args[1]['kwargs']['message']
        )
    
    @mock.patch('core.tasks.send_mail.apply_async')
    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publish_emails_user_on_fail(self, publish_mock, email_mock):
        profile_view(self.make_request())
        publish_mock.assert_called_once()
        
        delete_instance(self.scoreset)
        publish_scoreset.apply(**publish_mock.call_args[1])
        
        email_mock.assert_called()
        self.assertEqual(
            email_mock.call_args[1]['kwargs']['recipient_list'],
            [self.user.email]
        )
        self.assertIn(
            'could not be processed',
            email_mock.call_args[1]['kwargs']['message']
        )
        self.assertIn(
            reverse('accounts:profile'),
            email_mock.call_args[1]['kwargs']['message']
        )

    @mock.patch('dataset.tasks.publish_scoreset.apply_async')
    def test_publish_failure_saves_task(self, publish_mock):
        profile_view(self.make_request())
        publish_mock.assert_called_once()
    
        delete_instance(self.scoreset)
        publish_scoreset.apply(**publish_mock.call_args[1])
        self.assertEqual(FailedTask.objects.count(), 1)
        
        
class TestContributorSummaryView(TestCase, TestMessageMixin):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = UserFactory(username="adminman")
        self.scoreset = ScoreSetFactory()
        self.experiment = ExperimentFactory()
        self.experimentset = ExperimentSetFactory()
        
    def test_404_cannot_find_urn(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        with self.assertRaises(Http404):
            ContributorSummary.as_view()(request, urn='urn:maved:00000001-a-1')
        
    def test_permission_error_no_view_permissions(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        with self.assertRaises(PermissionDenied):
            ContributorSummary.as_view()(request, urn=self.scoreset.urn)
        
    def test_correctly_sets_model_and_qs_scoreset_urn(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        self.scoreset.add_administrators(self.admin)
        response = ContributorSummary.as_view()(request, urn=self.scoreset.urn)
        self.assertContains(response, self.admin.profile.get_display_name())
        
    def test_correctly_sets_model_and_qs_experiment_urn(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        self.experiment.add_administrators(self.admin)
        response = ContributorSummary.as_view()(request, urn=self.experiment.urn)
        self.assertContains(response, self.admin.profile.get_display_name())
        
    def test_correctly_sets_model_and_qs_experimentset_urn(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        self.experimentset.add_administrators(self.admin)
        response = ContributorSummary.as_view()(request, urn=self.experimentset.urn)
        self.assertContains(response, self.admin.profile.get_display_name())
        
    def test_edit_button_visible_for_admins(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        self.scoreset.add_administrators(self.admin)
        response = ContributorSummary.as_view()(request, urn=self.scoreset.urn)
        self.assertContains(response, '>Edit<')
        
    def test_edit_button_hidden_for_non_admins(self):
        request = self.create_request(method='get', path='/',)
        request.user = self.admin
        self.scoreset.add_editors(self.admin)
        response = ContributorSummary.as_view()(request, urn=self.scoreset.urn)
        self.assertNotContains(response, '>Edit<')
