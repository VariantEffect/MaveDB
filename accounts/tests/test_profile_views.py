from django.core.urlresolvers import reverse_lazy
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.core.exceptions import PermissionDenied

from dataset.factories import ExperimentSetFactory

from core.utilities.tests import TestMessageMixin

from ..factories import UserFactory
from ..permissions import (
    assign_user_as_instance_admin,
    assign_user_as_instance_viewer,
    user_is_admin_for_instance,
    user_is_viewer_for_instance
)

from ..views import manage_instance


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


class TestProfileManageInstanceView(TestCase, TestMessageMixin):
    def setUp(self):
        self.factory = RequestFactory()
        self.alice = UserFactory(username="alice", password="secret")
        self.bob = UserFactory(username="bob", password="secret")
        self.client.logout()

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

    def test_removes_existing_admin(self):
        obj = ExperimentSetFactory()
        assign_user_as_instance_admin(self.alice, obj)
        request = self.create_request(
            method='post',
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
        request = self.create_request(
            method='post',
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
        request = self.create_request(
            method='post',
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
        request = self.create_request(
            method='post',
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
        request = self.create_request(
            method='post',
            path='/profile/manage/{}/'.format(obj.urn),
            data={
                "viewers[]": [10000],
                "viewer_management-users": [10000]
            }
        )
        request.user = self.alice
        response = manage_instance(request, urn=obj.urn)
        self.assertEqual(response.status_code, 200)
