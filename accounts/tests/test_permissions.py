import factory

from django.db.models import signals
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment

from dataset import factories as ds_factories
from variant import factories as v_factories

from .. import permissions, factories


User = get_user_model()


class UtilitiesTest(TestCase):
    def setUp(self):
        self.exps = ds_factories.ExperimentSetFactory()
        self.exp = ds_factories.ExperimentFactory(experimentset=self.exps)
        self.scs = ds_factories.ScoreSetFactory(experiment=self.exp)
        self.var = v_factories.VariantFactory(scoreset=self.scs)
        self.user1 = factories.UserFactory()
        self.user2 = factories.UserFactory()
        self.user3 = factories.UserFactory()
        self.user4 = factories.UserFactory()

    def test_can_detect_valid_instance(self):
        self.assertTrue(permissions.valid_model_instance(self.exps))
        self.assertTrue(permissions.valid_model_instance(self.exp))
        self.assertTrue(permissions.valid_model_instance(self.scs))

    def test_can_detect_invalid_instance(self):
        self.assertFalse(permissions.valid_model_instance(ExperimentSet()))
        self.assertFalse(permissions.valid_model_instance(self.var))

    def test_can_get_admin_group_name_for_instance(self):
        group_name = permissions.get_admin_group_name_for_instance(self.exps)
        self.assertEqual(
            group_name, '{}:{}-administrator'.format(
                self.exps.class_name(), self.exps.pk))

    def test_can_get_editor_group_name_for_instance(self):
        group_name = permissions.get_editor_group_name_for_instance(self.exps)
        self.assertEqual(
            group_name, '{}:{}-editor'.format(
                self.exps.class_name(), self.exps.pk))

    def test_can_get_viewer_group_name_for_instance(self):
        group_name = permissions.get_viewer_group_name_for_instance(self.exps)
        self.assertEqual(
            group_name, '{}:{}-viewer'.format(
                self.exps.class_name(), self.exps.pk))
        
    def test_user_is_anon(self):
        self.assertTrue(
            permissions.user_is_anonymous(AnonymousUser()))
        self.assertFalse(
            permissions.user_is_anonymous(factories.UserFactory()))
        
    def test_valid_group(self):
        self.assertTrue(
            permissions.valid_group_type(permissions.GroupTypes.ADMIN))
        self.assertTrue(
            permissions.valid_group_type(permissions.GroupTypes.EDITOR))
        self.assertTrue(
            permissions.valid_group_type(permissions.GroupTypes.VIEWER))
        self.assertFalse(
            permissions.valid_group_type('not a group'))
    
    def test_user_is_admin_for_instance(self):
        self.exps.add_administrators(self.user1)
        self.assertIn(self.user1, self.exps.administrators)
        self.assertNotIn(self.user2, self.exps.administrators)

    def test_user_is_editor_for_instance(self):
        self.exps.add_editors(self.user1)
        self.assertIn(self.user1, self.exps.editors)
        self.assertNotIn(self.user2, self.exps.editors)
        
    def test_user_is_viewer_for_instance(self):
        self.exps.add_viewers(self.user1)
        self.assertIn(self.user1, self.exps.viewers)
        self.assertNotIn(self.user2, self.exps.viewers)
    
    def test_user_is_contributor_for_instance(self):
        self.exps.add_administrators(self.user1)
        self.exps.add_editors(self.user2)
        self.exps.add_viewers(self.user3)
        self.assertIn(self.user1, self.exps.contributors)
        self.assertIn(self.user2, self.exps.contributors)
        self.assertIn(self.user3, self.exps.contributors)
        self.assertNotIn(self.user4, self.exps.contributors)
    
    def test_instances_for_user_returns_instance_user_if_admin_for(self):
        self.exps.add_administrators(self.user1)
        self.exp.add_viewers(self.user1)
        result = permissions.instances_for_user_with_group_permission(
            self.user1, ExperimentSet, permissions.GroupTypes.ADMIN)
        self.assertEqual(result.count(), 1)
        self.assertIn(self.exps, result)
        
    def test_instances_for_user_returns_instance_user_if_editor_for(self):
        self.exps.add_editors(self.user1)
        self.exp.add_viewers(self.user1)
        result = permissions.instances_for_user_with_group_permission(
            self.user1, ExperimentSet, permissions.GroupTypes.EDITOR)
        self.assertEqual(result.count(), 1)
        self.assertIn(self.exps, result)
        
    def test_instances_for_user_returns_instance_user_if_viewer_for(self):
        self.exps.add_viewers(self.user1)
        self.exp.add_editors(self.user1)
        result = permissions.instances_for_user_with_group_permission(
            self.user1, ExperimentSet, permissions.GroupTypes.VIEWER)
        self.assertEqual(result.count(), 1)
        self.assertIn(self.exps, result)

    def test_anon_user_returns_empty_qs(self):
        result = permissions.instances_for_user_with_group_permission(
            AnonymousUser(), ExperimentSet, permissions.GroupTypes.ADMIN
        )
        self.assertEqual(result.count(), 0)
        

class GroupConstructionTest(TestCase):
    # Mute pre/post save the signals so we don't create the groups
    # when the objects.create method is invoked. We want to try creating
    # them manually.
    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUp(self):
        self.instance = ExperimentSet.objects.create()

    def test_can_make_admin_group_for_instance(self):
        permissions.create_admin_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(
            Group.objects.all()[0].name,
            '{}:{}-{}'.format(
                self.instance.class_name(), self.instance.pk,
                permissions.GroupTypes.ADMIN)
        )

    def test_can_make_contributor_group_for_instance(self):
        permissions.create_editor_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(
            Group.objects.all()[0].name,
            '{}:{}-{}'.format(
                self.instance.class_name(), self.instance.pk,
                permissions.GroupTypes.EDITOR)
        )

    def test_can_make_viewer_group_for_instance(self):
        permissions.create_viewer_group_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 1)
        self.assertEqual(
            Group.objects.all()[0].name,
            '{}:{}-{}'.format(
                self.instance.class_name(), self.instance.pk,
                permissions.GroupTypes.VIEWER)
        )

    def test_can_make_all_groups_for_instance(self):
        permissions.create_all_groups_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 3)


class GroupDeletionTest(TestCase):
    def setUp(self):
        self.instance = ExperimentSet.objects.create()

    def test_can_delete_admin_group_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        group_name = permissions.delete_admin_group_for_instance(
            self.instance)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(
            group_name,
            '{}:{}-{}'.format(
                self.instance.class_name(), self.instance.pk,
                permissions.GroupTypes.ADMIN)
        )

    def test_can_delete_contributor_group_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        group_name = permissions.delete_editor_group_for_instance(
            self.instance)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(
            group_name,
            '{}:{}-{}'.format(
                self.instance.class_name(), self.instance.pk,
                permissions.GroupTypes.EDITOR)
        )

    def test_can_delete_viewer_group_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        group_name = permissions.delete_viewer_group_for_instance(
            self.instance)
        self.assertEqual(Group.objects.count(), 2)
        self.assertEqual(
            group_name,
            '{}:{}-{}'.format(
                self.instance.class_name(), self.instance.pk,
                permissions.GroupTypes.VIEWER)
        )

    def test_can_delete_all_groups_for_instance(self):
        self.assertEqual(Group.objects.count(), 3)
        permissions.delete_all_groups_for_instance(self.instance)
        self.assertEqual(Group.objects.count(), 0)


class UserAssignmentToInstanceGroupTest(TestCase):

    @factory.django.mute_signals(signals.pre_save, signals.post_save)
    def setUp(self):
        self.instance_1 = ExperimentSet.objects.create()
        self.instance_2 = ExperimentSet.objects.create()
        self.user = factories.UserFactory()

    def type_error_add_non_user(self):
        with self.assertRaises(TypeError):
            permissions.assign_user_as_instance_admin(
                "", self.instance_1)
        with self.assertRaises(TypeError):
            permissions.assign_user_as_instance_editor(
                [], self.instance_1)
        with self.assertRaises(TypeError):
            permissions.assign_user_as_instance_viewer(
                User.objects, self.instance_1)

    def type_error_remove_non_user(self):
        with self.assertRaises(TypeError):
            permissions.remove_user_as_instance_admin(
                "", self.instance_1)
        with self.assertRaises(TypeError):
            permissions.remove_user_as_instance_editor(
                [], self.instance_1)
        with self.assertRaises(TypeError):
            permissions.remove_user_as_instance_viewer(
                User.objects, self.instance_1)
    
    def test_permissions_removed_when_deleting_group(self):
        user = self.user
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

        permissions.delete_admin_group_for_instance(self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_correct_permissions_assigned_to_admin_group(self):
        user = self.user
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

    def test_admin_permissions_removed_when_removing_user(self):
        user = self.user
        permissions.remove_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_correct_permissions_assigned_to_contributor_group(self):
        user = self.user
        permissions.assign_user_as_instance_editor(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

    def test_contributor_permissions_removed_when_removing_user(self):
        user = self.user
        permissions.assign_user_as_instance_editor(user, self.instance_1)
        permissions.remove_user_as_instance_editor(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_correct_permissions_assigned_to_viewer_group(self):
        user = self.user
        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertTrue(can_view)

    def test_viewer_permissions_removed_when_removing_user(self):
        user = self.user
        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        permissions.remove_user_as_instance_viewer(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertFalse(can_view)

    def test_cannot_assign_anon_user(self):
        user = AnonymousUser()
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        self.assertEqual(Group.objects.count(), 0)
        self.assertNotIn(user, self.instance_1.administrators)

    def test_default_user_not_does_not_belong_to_any_groups(self):
        user = self.user
        self.assertNotIn(user, self.instance_1.administrators)
        self.assertNotIn(user, self.instance_1.contributors)
        self.assertNotIn(user, self.instance_1.editors)
        self.assertNotIn(user, self.instance_1.viewers)

    def test_user_can_only_belong_to_one_group(self):
        user = self.user
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        self.assertIn(user, self.instance_1.administrators)

        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        self.assertNotIn(user, self.instance_1.administrators)
        self.assertIn(user, self.instance_1.viewers)

    def test_changing_user_groups_updates_permissions(self):
        user = self.user
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, self.instance_1)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, self.instance_1)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, self.instance_1)
        self.assertFalse(can_manage)
        self.assertFalse(can_edit)
        self.assertTrue(can_view)

    def test_administrators_get_all_permissions(self):
        user = self.user
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        self.assertIn(user, self.instance_1.administrators)
        self.assertTrue(
            user.has_perm(
                permissions.PermissionTypes.CAN_MANAGE, self.instance_1))
        self.assertTrue(
            user.has_perm(
                permissions.PermissionTypes.CAN_EDIT, self.instance_1))
        self.assertTrue(
            user.has_perm(
                permissions.PermissionTypes.CAN_VIEW, self.instance_1))

    def test_editors_get_edit_and_view_perms(self):
        user = self.user
        permissions.assign_user_as_instance_editor(user, self.instance_1)
        self.assertIn(user, self.instance_1.editors)
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_MANAGE, self.instance_1))
        self.assertTrue(
            user.has_perm(
                permissions.PermissionTypes.CAN_EDIT, self.instance_1))
        self.assertTrue(
            user.has_perm(
                permissions.PermissionTypes.CAN_VIEW, self.instance_1))

    def test_viewers_get_view_perm(self):
        user = self.user
        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        self.assertIn(user, self.instance_1.viewers)
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_MANAGE, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_EDIT, self.instance_1))
        self.assertTrue(
            user.has_perm(
                permissions.PermissionTypes.CAN_VIEW, self.instance_1))

    def test_removing_admin_removes_permissions(self):
        user = self.user
        permissions.assign_user_as_instance_admin(user, self.instance_1)
        self.assertIn(user, self.instance_1.administrators)

        permissions.remove_user_as_instance_admin(user, self.instance_1)
        self.assertNotIn(user, self.instance_1.administrators)
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_MANAGE, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_EDIT, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_VIEW, self.instance_1))

    def test_removing_editor_removes_permissions(self):
        user = self.user
        permissions.assign_user_as_instance_editor(user, self.instance_1)
        self.assertIn(user, self.instance_1.editors)

        permissions.remove_user_as_instance_editor(user, self.instance_1)
        self.assertNotIn(user, self.instance_1.editors)
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_MANAGE, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_EDIT, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_VIEW, self.instance_1))

    def test_removing_viewer_removes_permissions(self):
        user = self.user
        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        self.assertIn(user, self.instance_1.viewers)

        permissions.remove_user_as_instance_viewer(user, self.instance_1)
        self.assertNotIn(user, self.instance_1.viewers)
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_MANAGE, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_EDIT, self.instance_1))
        self.assertFalse(
            user.has_perm(
                permissions.PermissionTypes.CAN_VIEW, self.instance_1))

    def test_adding_user_to_group_is_idempotent(self):
        user = self.user
        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        permissions.assign_user_as_instance_viewer(user, self.instance_1)
        self.assertEqual(user.groups.count(), 1)

    def test_update_admin_group_empty_list_removes_all(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_admin(bob, self.instance_1)
        permissions.assign_user_as_instance_admin(alice, self.instance_1)

        self.assertIn(bob, self.instance_1.administrators)
        self.assertIn(alice, self.instance_1.administrators)

        permissions.update_admin_list_for_instance([], self.instance_1)
        self.assertNotIn(bob, self.instance_1.administrators)
        self.assertNotIn(alice, self.instance_1.administrators)

    def test_can_update_admin_group_with_user_list(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_admin(bob, self.instance_1)
        permissions.assign_user_as_instance_admin(alice, self.instance_1)

        self.assertIn(bob, self.instance_1.administrators)
        self.assertIn(alice, self.instance_1.administrators)

        permissions.update_admin_list_for_instance([alice], self.instance_1)
        self.assertNotIn(bob, self.instance_1.administrators)
        self.assertIn(alice, self.instance_1.administrators)

    def test_update_admin_editor_empty_list_removes_all(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_editor(bob, self.instance_1)
        permissions.assign_user_as_instance_editor(alice, self.instance_1)

        self.assertIn(bob, self.instance_1.editors)
        self.assertIn(alice, self.instance_1.editors)

        permissions.update_editor_list_for_instance([], self.instance_1)
        self.assertNotIn(bob, self.instance_1.editors)
        self.assertNotIn(alice, self.instance_1.editors)

    def test_can_update_editor_group_with_user_list(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_editor(bob, self.instance_1)
        permissions.assign_user_as_instance_editor(alice, self.instance_1)

        self.assertIn(bob, self.instance_1.editors)
        self.assertIn(alice, self.instance_1.editors)

        permissions.update_editor_list_for_instance([alice], self.instance_1)
        self.assertNotIn(bob, self.instance_1.editors)
        self.assertIn(alice, self.instance_1.editors)

    def test_update_viewer_group_empty_list_removes_all(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_viewer(bob, self.instance_1)
        permissions.assign_user_as_instance_viewer(alice, self.instance_1)

        self.assertIn(bob, self.instance_1.viewers)
        self.assertIn(alice, self.instance_1.viewers)

        permissions.update_viewer_list_for_instance([], self.instance_1)
        self.assertNotIn(bob, self.instance_1.viewers)
        self.assertNotIn(alice, self.instance_1.viewers)

    def test_can_update_viewer_group_with_user_list(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_viewer(bob, self.instance_1)
        permissions.assign_user_as_instance_viewer(alice, self.instance_1)

        self.assertIn(bob, self.instance_1.viewers)
        self.assertIn(alice, self.instance_1.viewers)

        permissions.update_viewer_list_for_instance([alice], self.instance_1)
        self.assertNotIn(bob, self.instance_1.viewers)
        self.assertIn(alice, self.instance_1.viewers)

    def test_can_get_instances_for_user_in_admin_group(self):
        bob = User.objects.create(username="bob")
        alice = User.objects.create(username="alice")
        permissions.assign_user_as_instance_admin(bob, self.instance_1)
        permissions.assign_user_as_instance_admin(alice, self.instance_2)

        alices = permissions.instances_for_user_with_group_permission(
            user=alice,
            model=ExperimentSet,
            group_type=permissions.GroupTypes.ADMIN
        )
        bobs = permissions.instances_for_user_with_group_permission(
            user=bob,
            model=ExperimentSet,
            group_type=permissions.GroupTypes.ADMIN
        )

        self.assertEqual(bobs[0], self.instance_1)
        self.assertEqual(alices[0], self.instance_2)

    def test_empty_list_returned_instances_for_user_in_group(self):
        alice = User.objects.create(username="alice")
        alices = permissions.instances_for_user_with_group_permission(
            user=alice,
            model=ExperimentSet,
            group_type=permissions.GroupTypes.ADMIN
        )
        self.assertEqual(len(alices), 0)

    def test_no_instances_returned_anon_user(self):
        user = AnonymousUser()
        anons = permissions.instances_for_user_with_group_permission(
            user=user,
            model=ExperimentSet,
            group_type=permissions.GroupTypes.ADMIN
        )
        self.assertEqual(len(anons), 0)

    def test_renaming_group_does_not_alter_permissions(self):
        user = self.user
        instance = ds_factories.ScoreSetFactory()
        permissions.assign_user_as_instance_admin(user, instance)

        # Test with old name
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, instance)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, instance)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, instance)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)

        old_name = '{}:{}-{}'.format(
            instance.class_name(), instance.pk,
            permissions.GroupTypes.ADMIN
        )
        new_name = '{}-{}'.format(
            instance.urn, permissions.GroupTypes.ADMIN)
        group = Group.objects.get(name=old_name)
        group.name = new_name
        group.save()

        # Test with new name
        instance.refresh_from_db()
        can_manage = user.has_perm(
            permissions.PermissionTypes.CAN_MANAGE, instance)
        can_edit = user.has_perm(
            permissions.PermissionTypes.CAN_EDIT, instance)
        can_view = user.has_perm(
            permissions.PermissionTypes.CAN_VIEW, instance)
        self.assertTrue(can_manage)
        self.assertTrue(can_edit)
        self.assertTrue(can_view)


class TestPermissionAreDisjoint(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        Experiment.objects.all().delete()
        ExperimentSet.objects.all().delete()
        User.objects.all().delete()

    def tearDown(self):
        Experiment.objects.all().delete()
        ExperimentSet.objects.all().delete()
        User.objects.all().delete()

    def test_assignment_is_disjoint_between_different_instances(self):
        experiment = ds_factories.ExperimentFactory()
        experimentset = experiment.experimentset
        self.assertEqual(experiment.pk, experimentset.pk)

        user = factories.UserFactory()
        permissions.assign_user_as_instance_admin(user, experiment)
        self.assertIn(user, experiment.administrators)
        self.assertNotIn(user, experimentset.administrators)

    def test_instances_for_user_does_not_partial_match_model_names(self):
        experiment = ds_factories.ExperimentFactory()
        experimentset = experiment.experimentset
        self.assertEqual(experiment.pk, experimentset.pk)

        user = factories.UserFactory()
        permissions.assign_user_as_instance_admin(user, experiment)
        instances = permissions.instances_for_user_with_group_permission(
            user=user, model=Experiment,
            group_type=permissions.GroupTypes.ADMIN
        )
        self.assertIn(experiment, instances)
        self.assertNotIn(experimentset, instances)
