from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group

from dataset.factories import ExperimentFactory
from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment

from ..factories import UserFactory
from ..permissions import GroupTypes
from .. import mixins


User = get_user_model()


class TestFunctions(TestCase):
    def setUp(self):
        self.instance = ExperimentFactory()
        self.user_a = UserFactory()
        self.user_b = UserFactory()
        self.user_c = UserFactory()

    def test_filter_anon_filters_out_anon(self):
        anon = AnonymousUser()
        result = mixins.filter_anon(User.objects.all())
        self.assertEqual(result.count(), 3)
        self.assertNotIn(anon, result)

    def test_add_users_adds_viewers(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.VIEWER)
        self.assertIn(self.user_a, self.instance.viewers)
        self.assertNotIn(self.user_a, self.instance.editors)
        self.assertNotIn(self.user_a, self.instance.administrators)

    def test_add_users_adds_editors(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.EDITOR)
        self.assertNotIn(self.user_a, self.instance.viewers)
        self.assertIn(self.user_a, self.instance.editors)
        self.assertNotIn(self.user_a, self.instance.administrators)

    def test_add_users_adds_administrators(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.ADMIN)
        self.assertNotIn(self.user_a, self.instance.viewers)
        self.assertNotIn(self.user_a, self.instance.editors)
        self.assertIn(self.user_a, self.instance.administrators)

    def test_remove_users_removes_viewers(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.VIEWER)
        mixins._remove_users(self.instance, self.user_a, GroupTypes.VIEWER)
        self.assertNotIn(self.user_a, self.instance.viewers)

    def test_remove_users_removes_editors(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.EDITOR)
        mixins._remove_users(self.instance, self.user_a, GroupTypes.EDITOR)
        self.assertNotIn(self.user_a, self.instance.editors)

    def test_remove_users_removes_administrators(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.ADMIN)
        mixins._remove_users(self.instance, self.user_a, GroupTypes.ADMIN)
        self.assertNotIn(self.user_a, self.instance.administrators)

    def test_add_list_adds_all_users(self):
        all_assigned = mixins._add_users(
            users=[self.user_a, self.user_b, self.user_c],
            instance=self.instance,
            group=GroupTypes.ADMIN,
        )
        self.assertTrue(all_assigned)
        self.assertIn(self.user_a, self.instance.administrators)
        self.assertIn(self.user_b, self.instance.administrators)
        self.assertIn(self.user_c, self.instance.administrators)

    def test_remove_list_adds_all_users(self):
        mixins._add_users(self.instance, self.user_a, GroupTypes.ADMIN)
        mixins._add_users(self.instance, self.user_b, GroupTypes.ADMIN)
        mixins._add_users(self.instance, self.user_c, GroupTypes.ADMIN)
        all_assigned = mixins._add_users(
            users=[self.user_a, self.user_b, self.user_c],
            instance=self.instance,
            group=GroupTypes.ADMIN,
        )
        self.assertTrue(all_assigned)
        self.assertIn(self.user_a, self.instance.administrators)
        self.assertIn(self.user_b, self.instance.administrators)
        self.assertIn(self.user_c, self.instance.administrators)

    def test_valueerror_add_or_remove_unknown_group(self):
        with self.assertRaises(ValueError):
            mixins._add_users(self.instance, self.user_a, "invalid")
        with self.assertRaises(ValueError):
            mixins._add_users(self.instance, self.user_a, "invalid")

    def test_typeerror_add_or_remove_not_supported_iterable(self):
        with self.assertRaises(TypeError):
            mixins._add_users(self.instance, dict(), GroupTypes.ADMIN)
        with self.assertRaises(TypeError):
            mixins._add_users(self.instance, dict(), GroupTypes.ADMIN)


class TestGroupPermisionMixin(TestCase):
    """
    This class tests the methods of :class:`GroupPermissionMixin` by using
    :class:`ExperimentSet` as the driver class. The driver class is needed so
    we can associate instances with admin/contrib/viewer group permissions.
    """

    def setUp(self):
        self.instance_a = ExperimentFactory()
        self.instance_b = ExperimentFactory()
        self.user_a = UserFactory()
        self.user_b = UserFactory()
        self.user_c = UserFactory()

    def test_administrators_returns_admins_only(self):
        self.instance_a.add_administrators(self.user_a)
        self.instance_a.add_editors(self.user_b)
        self.instance_a.add_viewers(self.user_c)
        self.assertIn(self.user_a, self.instance_a.administrators)
        self.assertEqual(self.instance_a.administrators.count(), 1)

    def test_editors_returns_editors_only(self):
        self.instance_a.add_administrators(self.user_c)
        self.instance_a.add_editors(self.user_a)
        self.instance_a.add_viewers(self.user_b)
        self.assertIn(self.user_a, self.instance_a.editors)
        self.assertEqual(self.instance_a.editors.count(), 1)

    def test_viewers_returns_viewers_only(self):
        self.instance_a.add_administrators(self.user_b)
        self.instance_a.add_editors(self.user_c)
        self.instance_a.add_viewers(self.user_a)
        self.assertIn(self.user_a, self.instance_a.viewers)
        self.assertEqual(self.instance_a.viewers.count(), 1)

    def test_contributors_returns_admins_editors_and_viewers(self):
        self.instance_a.add_administrators(self.user_a)
        self.instance_a.add_editors(self.user_b)
        self.instance_a.add_viewers(self.user_c)
        self.assertIn(self.user_a, self.instance_a.contributors)
        self.assertIn(self.user_b, self.instance_a.contributors)
        self.assertIn(self.user_c, self.instance_a.contributors)

    def test_contributors_returns_none_if_group_name_not_found(self):
        self.instance_a.add_administrators(self.user_a)
        self.assertIn(self.user_a, self.instance_a.contributors)

        Group.objects.get(name=self.instance_a.admin_group_name).delete()
        self.assertNotIn(self.user_a, self.instance_a.contributors)

    def test_can_remove_admin(self):
        self.instance_a.add_administrators(self.user_b)
        self.assertIn(self.user_b, self.instance_a.administrators)
        self.instance_a.remove_administrators(self.user_b)
        self.assertNotIn(self.user_b, self.instance_a.administrators)

    def test_can_remove_editor(self):
        self.instance_a.add_editors(self.user_b)
        self.assertIn(self.user_b, self.instance_a.editors)
        self.instance_a.remove_editors(self.user_b)
        self.assertNotIn(self.user_b, self.instance_a.editors)

    def test_can_remove_viewer(self):
        self.instance_a.add_viewers(self.user_b)
        self.assertIn(self.user_b, self.instance_a.viewers)
        self.instance_a.remove_viewers(self.user_b)
        self.assertNotIn(self.user_b, self.instance_a.viewers)


class TestgPermissionGroupsAreDisjoint(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        Experiment.objects.all().delete()
        ExperimentSet.objects.all().delete()
        User.objects.all().delete()

    def tearDown(self):
        Experiment.objects.all().delete()
        ExperimentSet.objects.all().delete()
        User.objects.all().delete()

    def test_result_is_disjoint_between_different_groups(self):
        experiment = ExperimentFactory()
        user1 = UserFactory()
        user2 = UserFactory()
        experiment.add_administrators(user1)
        experiment.add_editors(user2)
        self.assertIn(user1, experiment.administrators)
        self.assertNotIn(user2, experiment.administrators)

        self.assertNotIn(user1, experiment.editors)
        self.assertIn(user2, experiment.editors)

    def test_instances_for_user_does_not_partial_match_model_names(self):
        experiment = ExperimentFactory()
        experimentset = experiment.experimentset
        self.assertEqual(experiment.pk, experimentset.pk)

        user = UserFactory()
        experiment.add_administrators(user)
        self.assertIn(user, experiment.administrators)
        self.assertNotIn(user, experimentset.administrators)

    def test_contributors_returns_all_admins_editors_and_viewers(self):
        experiment = ExperimentFactory()
        experimentset = experiment.experimentset
        self.assertEqual(experiment.pk, experimentset.pk)

        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        user4 = UserFactory()

        experiment.add_administrators(user1)
        experiment.add_editors(user2)
        experiment.add_viewers(user3)

        self.assertIn(user1, experiment.contributors)
        self.assertIn(user2, experiment.contributors)
        self.assertIn(user3, experiment.contributors)
        self.assertNotIn(user4, experiment.contributors)
