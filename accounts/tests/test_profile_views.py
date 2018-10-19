import json
import mock

from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.http import Http404

from dataset import factories as ds_factories
from variant.factories import VariantFactory

from core.utilities.tests import TestMessageMixin

from ..factories import UserFactory
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
        
    def test_ajax_call_creates_new_token(self):
        user = UserFactory()
        self.assertIsNone(user.profile.auth_token)
        self.assertIsNone(user.profile.auth_token_expiry)
        request = self.create_request(
            method='get',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            path='/profile/',
        )
        request.user = user
        response = profile_settings(request)
        data = json.loads(response.content.decode())
        self.assertIsNotNone(user.profile.auth_token)
        self.assertIsNotNone(user.profile.auth_token_expiry)
        self.assertEqual(data['token'], user.profile.auth_token)
        self.assertEqual(data['expiry'], str(user.profile.auth_token_expiry))


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
        self.instance = ds_factories.ExperimentSetFactory()
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
        self.scoreset = ds_factories.ScoreSetWithTargetFactory()
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
    
    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)
    
    @mock.patch("dataset.tasks.publish_scoreset.apply_async")
    def test_successful_publish_calls_publish_utility(self, patch):
        profile_view(self.make_request())
        patch.assert_called()
        
    def test_redirects_on_success(self):
        response = profile_view(self.make_request())
        self.assertEqual(response.status_code, 302)
        
    def test_does_not_redirect_if_cannot_publish(self):
        request = self.make_request()
        self.scoreset.remove_administrators(self.user)
        response = profile_view(request)
        self.assertEqual(response.status_code, 200)


class TestProfileDeleteInstance(TestCase, TestMessageMixin):
    """
    Test the home view loads the correct template and requires a login.
    """
    def setUp(self):
        self.path = reverse_lazy("accounts:profile")
        self.factory = RequestFactory()
        self.instance = ds_factories.ScoreSetFactory()
        self.template = 'accounts/profile_home.html'
        self.user = UserFactory()
        self.post_data = {'delete': [self.instance.urn]}

    def make_request(self, user=None):
        data = self.post_data.copy()
        self.instance.add_administrators(self.user if user is None else user)
        request = self.create_request(method='post', path=self.path, data=data)
        request.user = self.user if user is None else user
        return request

    def test_requires_login(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 302)

    @mock.patch("dataset.tasks.delete_instance.apply_async")
    def test_successful_publish_calls_delete_utility(self, patch):
        profile_view(self.make_request())
        patch.assert_called()

    def test_redirects_on_success(self):
        response = profile_view(self.make_request())
        self.assertEqual(response.status_code, 302)

    def test_does_not_redirect_if_cannot_delete(self):
        request = self.make_request()
        self.instance.remove_administrators(self.user)
        response = profile_view(request)
        self.assertEqual(response.status_code, 200)