"""
This module defines stuff.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist

from guardian.shortcuts import assign_perm
from guardian.conf.settings import ANONYMOUS_USER_NAME

User = get_user_model()


# Base types
# -------------------------------------------------------------------------- #
class PermissionTypes:
    """
    A static utility class for defining permission types that groups can have.
    """
    CAN_VIEW = "can_view"
    CAN_EDIT = "can_edit"
    CAN_MANAGE = "can_manage"

    @classmethod
    def all(cls):
        return [cls.CAN_VIEW, cls.CAN_EDIT, cls.CAN_MANAGE]


class GroupTypes:
    """
    A static utility class for defining permission groups for instances such 
    as `ExperimentSet`, `Experiment` and `ScoreSet`.
    """
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    ADMIN = "administrator"

    @staticmethod
    def admin_permissions():
        return [
            PermissionTypes.CAN_VIEW,
            PermissionTypes.CAN_EDIT,
            PermissionTypes.CAN_MANAGE
        ]

    @staticmethod
    def contributor_permissions():
        return [
            PermissionTypes.CAN_VIEW,
            PermissionTypes.CAN_EDIT
        ]

    @staticmethod
    def viewer_permissions():
        return [
            PermissionTypes.CAN_VIEW
        ]


# Utilities
# --------------------------------------------------------------------------- #
def valid_model_instance(instance):
    from dataset.models.base import DatasetModel

    if not hasattr(instance, 'urn'):
        return False
    if not getattr(instance, 'urn'):
        return False
    if not isinstance(instance, DatasetModel):
        return False
    return True


def valid_group_type(group):
    return group in {
        GroupTypes.ADMIN, GroupTypes.CONTRIBUTOR, GroupTypes.VIEWER
    }


def user_is_anonymous(user):
    return isinstance(user, AnonymousUser) or \
        user.username == ANONYMOUS_USER_NAME


def get_admin_group_name_for_instance(instance):
    if valid_model_instance(instance):
        return '{}-{}'.format(instance.urn, GroupTypes.ADMIN)


def get_contributor_group_name_for_instance(instance):
    if valid_model_instance(instance):
        return '{}-{}'.format(instance.urn, GroupTypes.CONTRIBUTOR)


def get_viewer_group_name_for_instance(instance):
    if valid_model_instance(instance):
        return '{}-{}'.format(instance.urn, GroupTypes.VIEWER)


def user_is_admin_for_instance(user, instance):
    group_name = get_admin_group_name_for_instance(instance)
    if group_name is not None:
        return group_name in set([g.name for g in user.groups.all()])
    else:
        return False


def user_is_contributor_for_instance(user, instance):
    group_name = get_contributor_group_name_for_instance(instance)
    if group_name is not None:
        return group_name in set([g.name for g in user.groups.all()])
    else:
        return False


def user_is_viewer_for_instance(user, instance):
    group_name = get_viewer_group_name_for_instance(instance)
    if group_name is not None:
        return group_name in set([g.name for g in user.groups.all()])
    else:
        return False


GROUP_TYPE_CALLBACK = {
    GroupTypes.ADMIN: user_is_admin_for_instance,
    GroupTypes.CONTRIBUTOR: user_is_contributor_for_instance,
    GroupTypes.VIEWER: user_is_viewer_for_instance
}


def instances_for_user_with_group_permission(user, model, group_type):
    from dataset.models.experimentset import ExperimentSet
    from dataset.models.experiment import Experiment
    from dataset.models.scoreset import ScoreSet

    if user_is_anonymous(user):
        return []

    if model == ExperimentSet:
        instances = ExperimentSet.objects.all().order_by("urn")
    elif model == Experiment:
        instances = Experiment.objects.all().order_by("urn")
    elif model == ScoreSet:
        instances = ScoreSet.objects.all().order_by("urn")
    else:
        raise TypeError("Unrecognised model type {}.".format(model))

    is_in_group = GROUP_TYPE_CALLBACK.get(group_type, None)
    if is_in_group is None:
        raise ValueError("Unrecognised group type {}.".format(group_type))

    return [i for i in instances if is_in_group(user, i)]


def contributors_for_instance(instance):
    author_pks = set()
    if not valid_model_instance(instance):
        raise TypeError("Invalid type supplied {}".format(type(instance)))
    users = User.objects.all()
    for u in users:
        if user_is_admin_for_instance(u, instance):
            author_pks.add(u.pk)
        elif user_is_contributor_for_instance(u, instance):
            author_pks.add(u.pk)
    return User.objects.filter(pk__in=author_pks)


# Group construction
# --------------------------------------------------------------------------- #
def create_admin_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_admin_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).exists():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.admin_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def create_contributor_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_contributor_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).exists():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.contributor_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def create_viewer_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_viewer_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).exists():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.viewer_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def create_all_groups_for_instance(instance):
    if valid_model_instance(instance):
        g1 = create_admin_group_for_instance(instance)
        g2 = create_contributor_group_for_instance(instance)
        g3 = create_viewer_group_for_instance(instance)
        return g1, g2, g3


# Group deletion
# --------------------------------------------------------------------------- #
def delete_admin_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_admin_group_name_for_instance(instance)
        if Group.objects.filter(name=name).exists():
            group = Group.objects.get(name=name)
            group.delete()
            return name


def delete_contributor_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_contributor_group_name_for_instance(instance)
        if Group.objects.filter(name=name).exists():
            group = Group.objects.get(name=name)
            group.delete()
            return name


def delete_viewer_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_viewer_group_name_for_instance(instance)
        if Group.objects.filter(name=name).exists():
            group = Group.objects.get(name=name)
            group.delete()
            return name


def delete_all_groups_for_instance(instance):
    if valid_model_instance(instance):
        admin_name = delete_admin_group_for_instance(instance)
        author_name = delete_contributor_group_for_instance(instance)
        viewer_name = delete_viewer_group_for_instance(instance)
        return admin_name, author_name, viewer_name


# User assignment
# --------------------------------------------------------------------------- #
# Notes: A user should only be assigned to one group at any single time.
def assign_user_as_instance_admin(user, instance):
    if user_is_anonymous(user):
        return False

    group_name = get_admin_group_name_for_instance(instance)
    try:
        Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        create_admin_group_for_instance(instance)

    admin_group = Group.objects.get(name=group_name)
    remove_user_as_instance_contributor(user, instance)
    remove_user_as_instance_viewer(user, instance)
    user.groups.add(admin_group)
    user.save()
    return True


def assign_user_as_instance_contributor(user, instance):
    if user_is_anonymous(user):
        return False

    group_name = get_contributor_group_name_for_instance(instance)
    try:
        Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        create_contributor_group_for_instance(instance)

    author_group = Group.objects.get(name=group_name)
    remove_user_as_instance_admin(user, instance)
    remove_user_as_instance_viewer(user, instance)
    user.groups.add(author_group)
    user.save()
    return True


def assign_user_as_instance_viewer(user, instance):
    if user_is_anonymous(user):
        return False

    group_name = get_viewer_group_name_for_instance(instance)
    try:
        Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        create_viewer_group_for_instance(instance)

    viewer_group = Group.objects.get(name=group_name)
    remove_user_as_instance_admin(user, instance)
    remove_user_as_instance_contributor(user, instance)
    user.groups.add(viewer_group)
    user.save()
    return True


# User removal
# --------------------------------------------------------------------------- #
def remove_user_as_instance_admin(user, instance):
    try:
        group_name = get_admin_group_name_for_instance(instance)
        admin_group = Group.objects.get(name=group_name)
        user.groups.remove(admin_group)
        user.save()
        return True
    except ObjectDoesNotExist:
        return False


def remove_user_as_instance_contributor(user, instance):
    try:
        group_name = get_contributor_group_name_for_instance(instance)
        author_group = Group.objects.get(name=group_name)
        user.groups.remove(author_group)
        user.save()
        return True
    except ObjectDoesNotExist:
        return False


def remove_user_as_instance_viewer(user, instance):
    try:
        group_name = get_viewer_group_name_for_instance(instance)
        viewer_group = Group.objects.get(name=group_name)
        user.groups.remove(viewer_group)
        user.save()
        return True
    except ObjectDoesNotExist:
        return False


# Updates
# -------------------------------------------------------------------------- #
def update_admin_list_for_instance(users, instance):
    site_users = User.objects.all()
    for user in site_users:
        if user not in users:
            remove_user_as_instance_admin(user, instance)
    for user in users:
        assign_user_as_instance_admin(user, instance)


def update_contributor_list_for_instance(users, instance):
    site_users = User.objects.all()
    for user in site_users:
        if user not in users:
            remove_user_as_instance_contributor(user, instance)
    for user in users:
        assign_user_as_instance_contributor(user, instance)


def update_viewer_list_for_instance(users, instance):
    site_users = User.objects.all()
    for user in site_users:
        if user not in users:
            remove_user_as_instance_viewer(user, instance)
    for user in users:
        assign_user_as_instance_viewer(user, instance)
