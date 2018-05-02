from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from dataset.models.experimentset import ExperimentSet

from ..factories import UserFactory
from ..mixins import filter_su, filter_anon, UserSearchMixin
from ..permissions import (
    assign_user_as_instance_admin, assign_user_as_instance_editor,
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
        assign_user_as_instance_editor(self.bob, self.instance_a)
        result = self.instance_a.administrators()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_editors_returns_editors_only(self):
        assign_user_as_instance_editor(self.alice, self.instance_a)
        assign_user_as_instance_admin(self.bob, self.instance_a)
        result = self.instance_a.editors()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_viewers_returns_viewers_only(self):
        assign_user_as_instance_viewer(self.alice, self.instance_a)
        assign_user_as_instance_admin(self.bob, self.instance_a)
        result = self.instance_a.viewers()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_contributors_returns_admins_editors_and_viewers(self):
        jimmy = User.objects.create(username='jimmy', password='secret_key')
        assign_user_as_instance_admin(self.alice, self.instance_a)
        assign_user_as_instance_editor(self.bob, self.instance_a)
        assign_user_as_instance_viewer(jimmy, self.instance_a)
        result = self.instance_a.contributors()
        expected = [self.alice, self.bob, jimmy]
        self.assertEqual(expected, list(result.all()))

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
            [self.alice, self.bob],
            list(filter_anon(User.objects.all()))
        )


class TestUserSearchMixin(TestCase):

    searcher = UserSearchMixin()

    def test_can_search_by_first_name(self):
        u1 = UserFactory(first_name='Bob')
        u2 = UserFactory(first_name='Alice')

        dict_ = {'first_name': 'bob'}
        q = self.searcher.search_all(
            dict_, join_func=self.searcher.or_join_qs)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(u1, result)
        self.assertNotIn(u2, result)

    def test_can_search_by_last_name(self):
        u1 = UserFactory(last_name='Bob')
        u2 = UserFactory(last_name='Alice')

        dict_ = {'last_name': 'bob'}
        q = self.searcher.search_all(
            dict_, join_func=self.searcher.or_join_qs)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(u1, result)
        self.assertNotIn(u2, result)

    def test_can_search_by_username(self):
        u1 = UserFactory(username='Bob')
        u2 = UserFactory(username='Alice')

        dict_ = {'username': 'bob'}
        q = self.searcher.search_all(
            dict_, join_func=self.searcher.or_join_qs)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 1)
        self.assertIn(u1, result)
        self.assertNotIn(u2, result)

    def test_can_search_multiple_fields(self):
        u1 = UserFactory(username='Bob')
        u2 = UserFactory(first_name='Alice')
        u3 = UserFactory(first_name='Bob')

        dict_ = {'first_name': 'Alice', 'username': 'bob'}
        q = self.searcher.search_all(
            dict_, join_func=self.searcher.or_join_qs)

        result = User.objects.filter(q).distinct()
        self.assertEqual(result.count(), 2)
        self.assertIn(u1, result)
        self.assertIn(u2, result)
        self.assertNotIn(u3, result)
