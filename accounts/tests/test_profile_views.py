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

from ..factories import UserFactory
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer,
    assign_user_as_instance_editor,
)

from ..views import ManageDatasetUsersView, \
    profile_view, profile_settings


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
        _ = profile_view(request)
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
        instance = ScoreSetFactory()  # type: ScoreSet
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
        instance = ScoreSetFactory()  # type: ScoreSet
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
    
    def step_1_data(self):
        return {
            'manage_users-administrators': [self.user1.pk],
            'manage_users-editors': [self.user2.pk],
            'manage_users-viewers': [self.user3.pk],
            'manage_dataset_users_view-current_step': ['manage_users'],
            'submit': ['submit'],
        }
    
    def step_2_data(self):
        return {
            'manage_users-administrators': [self.user1.pk],
            'manage_users-editors': [self.user2.pk],
            'manage_users-viewers': [self.user3.pk],
            'manage_dataset_users_view-current_step': ['confirm_changes'],
            'submit': ['submit']
        }
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user1 = UserFactory(password="secret")
        self.user2 = UserFactory(password="secret")
        self.user3 = UserFactory(password="secret")
        self.raw_password = 'secret'
        self.instance = ExperimentSetFactory()
        self.variant = VariantFactory()
        self.path= reverse_lazy(
            'accounts:manage_instance',
            args=(self.instance.urn,)
        )
        self.client.logout()

    def login(self, user):
        self.client.login(
            username=user.username, password=self.raw_password)
        self.assertTrue(self.user1.is_authenticated)

    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)
        
    def test_403_no_manage_permission(self):
        self.instance.add_viewers(self.user1)
        self.login(self.user1)
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 403)
        
    def test_404_object_not_found(self):
        self.login(self.user1)
        response = self.client.get(self.path + 'blah')
        self.assertEqual(response.status_code, 404)
        
    def test_404_not_valid_model(self):
        # Need to use request here. Django client login is much too finicky
        # and randomly logs out during the request-response cycle.
        request = self.create_request('get', path=self.path)
        request.user = self.user1
        with self.assertRaises(Http404):
            ManageDatasetUsersView.as_view()(request, self.variant.urn)
            
    def test_summary_shows_updated_groups(self):
        self.instance.add_administrators(self.user1)
        self.login(self.user1)
        response = self.client.post(self.path, data=self.step_1_data())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['wizard']['steps'].current, 'confirm_changes')
        self.assertContains(response, self.user1.profile.get_display_name())
        self.assertContains(response, self.user2.profile.get_display_name())
        self.assertContains(response, self.user3.profile.get_display_name())
    

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
        