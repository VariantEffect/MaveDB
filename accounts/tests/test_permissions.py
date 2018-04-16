import factory

from django.db.models import signals
from django.contrib.auth.models import Group, AnonymousUser
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, TestCase

from accounts.permissions import PermissionTypes, GroupTypes
from accounts.permissions import (
    valid_model_instance,
    contributors_for_instance,

    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance,

    create_all_groups_for_instance,
    create_admin_group_for_instance,
    create_contributor_group_for_instance,
    create_viewer_group_for_instance,

    delete_all_groups_for_instance,
    delete_admin_group_for_instance,
    delete_contributor_group_for_instance,
    delete_viewer_group_for_instance,

    get_admin_group_name_for_instance,
    get_contributor_group_name_for_instance,
    get_viewer_group_name_for_instance,

    assign_user_as_instance_admin,
    assign_user_as_instance_contributor,
    assign_user_as_instance_viewer,

    remove_user_as_instance_admin,
    remove_user_as_instance_contributor,
    remove_user_as_instance_viewer,

    update_admin_list_for_instance,
    update_contributor_list_for_instance,
    update_viewer_list_for_instance,

    instances_for_user_with_group_permission
)

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet
from variant.models import Variant


User = get_user_model()


class UtilitiesTest(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.exps = ExperimentSet.objects.create()
        self.exp = Experiment.objects.create(experimentset=self.exps)
        self.scs = ScoreSet.objects.create(experiment=self.exp)
        self.var = Variant.objects.create(scoreset=self.scs, hgvs="test")

    def test_can_detect_valid_instance(self):
        self.assertTrue(valid_model_instance(self.exps))
        self.assertTrue(valid_model_instance(self.exp))
        self.assertTrue(valid_model_instance(self.scs))

    def test_can_detect_invalid_instance(self):
        self.assertFalse(valid_model_instance(ExperimentSet()))
        self.assertFalse(valid_model_instance(self.var))

    def test_can_get_admin_group_name_for_instance(self):
        group_name = get_admin_group_name_for_instance(self.exps)
        self.assertEqual(group_name, 'urn:mavedb:00000001-administrator')

    def test_can_get_contributor_group_name_for_instance(self):
        group_name = get_contributor_group_name_for_instance(self.exps)
        self.assertEqual(group_name, 'urn:mavedb:00000001-contributor')

    def test_can_get_viewer_group_name_for_instance(self):
        group_name = get_viewer_group_name_for_instance(self.exps)
        self.assertEqual(group_name, 'urn:mavedb:00000001-viewer')


class GroupConstructionTest(TestCase):
    # Mute pre/post save the signals so we don't create the groups
    # when the objects.create method is invoked. We want to try creating
    # them manually.
    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUp(self):
        self.instance = ExperimentSet.objects.create()

    def test_can_make_admin_group_for_instance(self):
        create_admin_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(
            Group.objects.all()[0].name,
            '{}-{}'.format(self.instance.urn, GroupTypes.ADMIN)
        )

    def test_can_make_contributor_group_for_instance(self):
        create_contributor_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(
            Group.objects.all()[0].name,
            '{}-{}'.format(self.instance.urn, GroupTypes.CONTRIBUTOR)
        )

    def test_can_make_viewer_group_for_instance(self):
        create_viewer_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(
            Group.objects.all()[0].name,
            '{}-{}'.format(self.instance.urn, GroupTypes.VIEWER)
        )

    def test_can_make_all_groups_for_instance(self):
        create_all_groups_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 3)


class GroupDeletionTest(TestCase):

    def setUp(self):
        self.instance = ExperimentSet.objects.create()

    def test_can_delete_admin_group_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        group_name = delete_admin_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(
            group_name,
            '{}-{}'.format(self.instance.urn, GroupTypes.ADMIN)
        )

    def test_can_delete_contributor_group_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        group_name = delete_contributor_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(
            group_name,
            '{}-{}'.format(self.instance.urn, GroupTypes.CONTRIBUTOR)
        )

    def test_can_delete_viewer_group_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        group_name = delete_viewer_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(
            group_name,
            '{}-{}'.format(self.instance.urn, GroupTypes.VIEWER)
        )

    def test_can_delete_all_groups_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        delete_all_groups_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 0)


class UserAssignmentToInstanceGroupTest(TestCase):

    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUp(self):
        self.instance_1 = ExperimentSet.objects.create()
        self.instance_2 = ExperimentSet.objects.create()

    def user(self):
        return User.objects.create(username="bob", password="pass")

    def test_permissions_removed_when_deleting_group(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

        delete_admin_group_for_instance(self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_correct_permissions_assigned_to_admin_group(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

    def test_admin_permissions_removed_when_removing_user(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        remove_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_correct_permissions_assigned_to_contributor_group(self):
        user = self.user()
        assign_user_as_instance_contributor(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

    def test_contributor_permissions_removed_when_removing_user(self):
        user = self.user()
        assign_user_as_instance_contributor(user, self.instance_1)
        remove_user_as_instance_contributor(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_correct_permissions_assigned_to_viewer_group(self):
        user = self.user()
        assign_user_as_instance_viewer(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertTrue(can_view)

    def test_viewer_permissions_removed_when_removing_user(self):
        user = self.user()
        assign_user_as_instance_viewer(user, self.instance_1)
        remove_user_as_instance_viewer(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_cannot_assign_anon_user(self):
        user = AnonymousUser()
        assign_user_as_instance_admin(user, self.instance_1)
        self.assertEqual(Group.objects.count(), 0)
        self.assertFalse(user_is_admin_for_instance(user, self.instance_1))

    def test_assignment_is_disjoint_between_different_instances(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        self.assertTrue(user_is_admin_for_instance(user, self.instance_1))
        self.assertFalse(user_is_admin_for_instance(user, self.instance_2))

    def test_default_user_not_does_not_belong_to_any_groups(self):
        user = self.user()
        self.assertFalse(user_is_admin_for_instance(user, self.instance_1))
        self.assertFalse(
            user_is_contributor_for_instance(user, self.instance_1))
        self.assertFalse(user_is_viewer_for_instance(user, self.instance_1))

    def test_user_can_only_belong_to_one_group(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        self.assertTrue(user_is_admin_for_instance(user, self.instance_1))

        assign_user_as_instance_viewer(user, self.instance_1)
        self.assertFalse(user_is_admin_for_instance(user, self.instance_1))
        self.assertTrue(user_is_viewer_for_instance(user, self.instance_1))

    def test_changing_user_groups_updates_permissions(self):
        user = self.user()

        assign_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

        assign_user_as_instance_viewer(user, self.instance_1)
        can_manage = user.has_perm(PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertTrue(can_view)

    def test_can_assign_user_as_admin(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        self.assertTrue(user_is_admin_for_instance(user, self.instance_1))

    def test_can_assign_user_as_contributor(self):
        user = self.user()
        assign_user_as_instance_contributor(user, self.instance_1)
        self.assertTrue(user_is_contributor_for_instance(user, self.instance_1))

    def test_can_assign_user_as_viewer(self):
        user = self.user()
        assign_user_as_instance_viewer(user, self.instance_1)
        self.assertTrue(user_is_viewer_for_instance(user, self.instance_1))

    def test_can_remove_user_from_admin_group(self):
        user = self.user()
        assign_user_as_instance_admin(user, self.instance_1)
        self.assertTrue(user_is_admin_for_instance(user, self.instance_1))
        remove_user_as_instance_admin(user, self.instance_1)
        self.assertFalse(user_is_admin_for_instance(user, self.instance_1))

    def test_can_remove_user_from_contributor_group(self):
        user = self.user()
        assign_user_as_instance_contributor(user, self.instance_1)
        self.assertTrue(user_is_contributor_for_instance(user, self.instance_1))

        remove_user_as_instance_contributor(user, self.instance_1)
        self.assertFalse(user_is_contributor_for_instance(user, self.instance_1))

    def test_can_remove_user_from_viewer_group(self):
        user = self.user()
        assign_user_as_instance_viewer(user, self.instance_1)
        self.assertTrue(user_is_viewer_for_instance(user, self.instance_1))
        remove_user_as_instance_viewer(user, self.instance_1)
        self.assertFalse(user_is_viewer_for_instance(user, self.instance_1))

    def test_adding_user_to_group_twice_does_nothing(self):
        user = self.user()
        assign_user_as_instance_viewer(user, self.instance_1)
        assign_user_as_instance_viewer(user, self.instance_1)
        self.assertEqual(user.groups.count(), 1)

    def test_update_admin_group_empty_list_removes_all(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_admin(bob, self.instance_1)
        assign_user_as_instance_admin(alice, self.instance_1)

        self.assertTrue(user_is_admin_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_admin_for_instance(alice, self.instance_1))

        update_admin_list_for_instance([], self.instance_1)
        self.assertFalse(user_is_admin_for_instance(bob, self.instance_1))
        self.assertFalse(user_is_admin_for_instance(alice, self.instance_1))

    def test_can_update_admin_group_with_user_list(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_admin(bob, self.instance_1)
        assign_user_as_instance_admin(alice, self.instance_1)

        self.assertTrue(user_is_admin_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_admin_for_instance(alice, self.instance_1))

        update_admin_list_for_instance([alice], self.instance_1)
        self.assertFalse(user_is_admin_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_admin_for_instance(alice, self.instance_1))

    def test_update_admin_contributor_empty_list_removes_all(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_contributor(bob, self.instance_1)
        assign_user_as_instance_contributor(alice, self.instance_1)

        self.assertTrue(user_is_contributor_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_contributor_for_instance(alice, self.instance_1))

        update_contributor_list_for_instance([], self.instance_1)
        self.assertFalse(user_is_contributor_for_instance(bob, self.instance_1))
        self.assertFalse(user_is_contributor_for_instance(alice, self.instance_1))

    def test_can_update_contributor_group_with_user_list(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_contributor(bob, self.instance_1)
        assign_user_as_instance_contributor(alice, self.instance_1)

        self.assertTrue(user_is_contributor_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_contributor_for_instance(alice, self.instance_1))

        update_contributor_list_for_instance([alice], self.instance_1)
        self.assertFalse(user_is_contributor_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_contributor_for_instance(alice, self.instance_1))

    def test_update_viewer_group_empty_list_removes_all(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_viewer(bob, self.instance_1)
        assign_user_as_instance_viewer(alice, self.instance_1)

        self.assertTrue(user_is_viewer_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_viewer_for_instance(alice, self.instance_1))

        update_viewer_list_for_instance([], self.instance_1)
        self.assertFalse(user_is_viewer_for_instance(bob, self.instance_1))
        self.assertFalse(user_is_viewer_for_instance(alice, self.instance_1))

    def test_can_update_viewer_group_with_user_list(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_viewer(bob, self.instance_1)
        assign_user_as_instance_viewer(alice, self.instance_1)

        self.assertTrue(user_is_viewer_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_viewer_for_instance(alice, self.instance_1))

        update_viewer_list_for_instance([alice], self.instance_1)
        self.assertFalse(user_is_viewer_for_instance(bob, self.instance_1))
        self.assertTrue(user_is_viewer_for_instance(alice, self.instance_1))

    def test_can_get_instances_for_user_in_admin_group(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        assign_user_as_instance_admin(bob, self.instance_1)
        assign_user_as_instance_admin(alice, self.instance_2)

        alices = instances_for_user_with_group_permission(
            user=alice,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )
        bobs = instances_for_user_with_group_permission(
            user=bob,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )

        self.assertEqual(bobs[0], self.instance_1)
        self.assertEqual(alices[0], self.instance_2)

    def test_empty_list_returned_instances_for_user_in_group(self):
        alice = User.objects.create(username="alice")
        alices = instances_for_user_with_group_permission(
            user=alice,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )
        self.assertEqual(len(alices), 0)

    def test_no_instances_returned_anon_user(self):
        user = AnonymousUser()
        anons = instances_for_user_with_group_permission(
            user=user,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )
        self.assertEqual(len(anons), 0)

    def test_error_incorrect_model_supplied(self):
        bob = User.objects.create(username="bob")
        with self.assertRaises(TypeError):
            instances_for_user_with_group_permission(
                user=bob,
                model=User,
                group_type=GroupTypes.ADMIN
            )

    def test_error_incorrect_group_type_supplied(self):
        bob = User.objects.create(username="bob")
        with self.assertRaises(ValueError):
            instances_for_user_with_group_permission(
                user=bob,
                model=ExperimentSet,
                group_type="InvalidGroup"
            )

    def test_can_get_contributors_for_instance(self):
        alice = User.objects.create(username="alice")
        bob = User.objects.create(username="bob")
        farva = User.objects.create(username="farva")

        assign_user_as_instance_admin(alice, self.instance_1)
        assign_user_as_instance_contributor(farva, self.instance_1)
        assign_user_as_instance_viewer(bob, self.instance_1)

        contributors = contributors_for_instance(self.instance_1)

        self.assertIn(alice, contributors)
        self.assertIn(farva, contributors)
        self.assertNotIn(bob, contributors)
