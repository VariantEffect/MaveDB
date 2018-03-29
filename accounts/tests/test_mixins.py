from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from dataset.models import ExperimentSet

from ..mixins import filter_su, filter_anon
from ..permissions import (
    assign_user_as_instance_admin, assign_user_as_instance_contributor,
    assign_user_as_instance_viewer
)


User = get_user_model()


class TestGroupPermisionMixin(TestCase):
    """
    This class tests the methods of :class:`GroupPermissionMixin` by using
    :class:`ExperimentSet` as the driver class. The driver class is needed so
    we can associate instances with admin/contrib/viewer group permissions.
    """
    def setUp(self):
        self.instance_a = ExperimentSet.objects.create()
        self.instance_b = ExperimentSet.objects.create()
        self.alice = User.objects.create(
            username='alice', password='secret_key')
        self.bob = User.objects.create(
            username='bob', password='secret_key')

    def test_administrators_returns_admins_only(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        assign_user_as_instance_contributor(self.bob, self.instance_a)
        result = self.instance_a.administrators()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_contributors_returns_contributors_only(self):
        assign_user_as_instance_contributor(self.alice, self.instance_a)
        assign_user_as_instance_admin(self.bob, self.instance_a)
        result = self.instance_a.contributors()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_viewers_returns_viewers_only(self):
        assign_user_as_instance_viewer(self.alice, self.instance_a)
        assign_user_as_instance_admin(self.bob, self.instance_a)
        result = self.instance_a.viewers()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_editors_returns_admins_and_contributors(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        assign_user_as_instance_contributor(self.bob, self.instance_a)
        result = self.instance_a.editors()
        expected = [self.alice, self.bob]
        self.assertEqual(expected, list(result.all()))

    def _format_as_returns_mononym_when_no_last_name(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        self.alice.first_name = 'Alice'

        result = self.instance_a.format_using_full_name(group='administrators')
        expected = [self.alice.first_name]
        self.assertEqual(result, expected)

        result = self.instance_a.format_using_short_name(group='administrators')
        expected = [self.alice.first_name]
        self.assertEqual(result, expected)

    def test_format_as_returns_short_name(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        self.alice.first_name = 'Alice'
        self.alice.last_name = 'Daniels'
        self.alice.save()

        result = self.instance_a.format_using_short_name(group='administrators')
        expected = [self.alice.get_short_name()]
        self.assertEqual(result, expected)

    def test_format_as_returns_full_name(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        self.alice.first_name = 'Alice'
        self.alice.last_name = 'Daniels'
        self.alice.save()

        result = self.instance_a.format_using_full_name(group='administrators')
        expected = [self.alice.get_full_name()]
        self.assertEqual(result, expected)

    def test_format_as_returns_usernames(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        result = self.instance_a.format_using_username(group='administrators')
        expected = [self.alice.username]
        self.assertEqual(result, expected)

    def test_format_comma_separates(self):
        assign_user_as_instance_admin(self.alice, self.instance_a)
        assign_user_as_instance_admin(self.bob, self.instance_a)
        result = self.instance_a.format_using_username(
            group='administrators', string=True)
        expected = ', '.join([self.alice.username, self.bob.username])
        self.assertEqual(result, expected)

    def test_filter_superuser_removes_superusers(self):
        self.alice.is_superuser = True
        self.alice.save()
        result = [self.bob]
        self.assertEqual(
            result, list(filter_anon(filter_su(User.objects.all()))))
        self.assertEqual(result, list(filter_su([self.alice, self.bob])))

    def test_filter_anon_removes_anon_users(self):
        self.assertEqual(
            [], filter_anon([AnonymousUser()])
        )
        self.assertEqual(
            [self.alice, self.bob], list(filter_anon(User.objects.all()))
        )