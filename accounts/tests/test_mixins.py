from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from dataset.models.experimentset import ExperimentSet

from ..factories import UserFactory
from ..permissions import PermissionTypes
from ..mixins import filter_su, filter_anon, UserFilterMixin


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
        self.joe = User.objects.create(
            username='joe', password='secret_key')
        
    def test_add_administrators_adds_correct_permissions(self):
        self.instance_a.add_administrators([self.alice])
        self.assertTrue(self.alice.has_perm(
            PermissionTypes.CAN_MANAGE, self.instance_a))
        self.assertTrue(self.alice.has_perm(
            PermissionTypes.CAN_EDIT, self.instance_a))
        self.assertTrue(self.alice.has_perm(
            PermissionTypes.CAN_VIEW, self.instance_a))
        
    def test_add_editors_adds_correct_permissions(self):
        self.instance_a.add_editors([self.alice])
        self.assertFalse(self.alice.has_perm(
            PermissionTypes.CAN_MANAGE, self.instance_a))
        self.assertTrue(self.alice.has_perm(
            PermissionTypes.CAN_EDIT, self.instance_a))
        self.assertTrue(self.alice.has_perm(
            PermissionTypes.CAN_VIEW, self.instance_a))

    def test_add_viewers_adds_correct_permissions(self):
        self.instance_a.add_viewers([self.alice])
        self.assertFalse(self.alice.has_perm(
            PermissionTypes.CAN_MANAGE, self.instance_a))
        self.assertFalse(self.alice.has_perm(
            PermissionTypes.CAN_EDIT, self.instance_a))
        self.assertTrue(self.alice.has_perm(
            PermissionTypes.CAN_VIEW, self.instance_a))

    def test_administrators_returns_admins_only(self):
        self.instance_a.add_administrators(self.alice)
        self.instance_a.add_editors(self.bob)
        self.instance_a.add_viewers(self.joe)
        result = self.instance_a.administrators()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_editors_returns_editors_only(self):
        self.instance_a.add_administrators(self.joe)
        self.instance_a.add_editors(self.alice)
        self.instance_a.add_viewers(self.bob)
        result = self.instance_a.editors()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_viewers_returns_viewers_only(self):
        self.instance_a.add_administrators(self.bob)
        self.instance_a.add_editors(self.joe)
        self.instance_a.add_viewers(self.alice)
        result = self.instance_a.viewers()
        expected = [self.alice]
        self.assertEqual(expected, list(result.all()))

    def test_contributors_returns_admins_editors_and_viewers(self):
        self.instance_a.add_administrators(self.alice)
        self.instance_a.add_editors(self.bob)
        self.instance_a.add_viewers(self.joe)
        result = self.instance_a.contributors()
        expected = [self.alice, self.bob, self.joe]
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

    def test_can_remove_admin(self):
        self.instance_a.add_administrators(self.alice)
        self.instance_a.add_administrators(self.bob)
        result = self.instance_a.administrators()
        expected = [self.alice, self.bob]
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

        self.instance_a.remove_administrators(self.alice)
        result = self.instance_a.administrators()
        expected = [self.bob]
        self.assertEqual(expected, list(result.all()))

    def test_can_remove_editor(self):
        self.instance_a.add_editors(self.alice)
        self.instance_a.add_editors(self.bob)
        result = self.instance_a.editors()
        expected = [self.alice, self.bob]
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

        self.instance_a.remove_editors(self.alice)
        result = self.instance_a.editors()
        expected = [self.bob]
        self.assertEqual(expected, list(result.all()))

    def test_can_remove_viewer(self):
        self.instance_a.add_viewers(self.alice)
        self.instance_a.add_viewers(self.bob)
        result = self.instance_a.viewers()
        expected = [self.alice, self.bob]
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

        self.instance_a.remove_viewers(self.alice)
        result = self.instance_a.viewers()
        expected = [self.bob]
        self.assertEqual(expected, list(result.all()))

    def test_can_add_list(self):
        self.instance_a.add_administrators(User.objects.all())
        result = self.instance_a.administrators()
        expected = [self.alice, self.bob, self.joe]
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

    def test_can_remove_list(self):
        self.instance_a.add_administrators(User.objects.all())
        result = self.instance_a.administrators()
        expected = [self.alice, self.bob, self.joe]
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

        self.instance_a.remove_administrators(User.objects.all())
        result = self.instance_a.administrators()
        expected = []
        self.assertListEqual(
            sorted(list(expected), key=lambda x: x.username),
            sorted(list(result.all()), key=lambda x: x.username)
        )

    def test_typeerror_add_or_remove_non_user_or_iterable(self):
        with self.assertRaises(TypeError):
            self.instance_a.add_administrators("4")
        with self.assertRaises(TypeError):
            self.instance_a.remove_administrators(User.objects)

    def test_filter_superuser_removes_superusers(self):
        self.alice.is_superuser = True
        self.joe.is_superuser = True
        self.alice.save()
        self.joe.save()
        result = [self.bob]
        self.assertEqual(
            result, list(filter_anon(filter_su(User.objects.all()))))
        self.assertEqual(result, list(filter_su([self.alice, self.bob])))

    def test_filter_anon_removes_anon_users(self):
        self.assertEqual(
            [], filter_anon([AnonymousUser()])
        )
        self.assertEqual(
            [self.alice, self.bob, self.joe],
            list(filter_anon(User.objects.all()))
        )


class TestUserSearchMixin(TestCase):

    searcher = UserFilterMixin()

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
