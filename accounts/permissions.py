"""
This module defines stuff.
"""

from django.contrib.auth.models import Group, User, AnonymousUser
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist

from guardian.shortcuts import assign_perm, remove_perm
from guardian.conf.settings import ANONYMOUS_USER_NAME


# Base types
# -------------------------------------------------------------------------- #
class PermissionTypes:
    """
    A static utility class for defining permission types that groups can have.
    """
    CAN_VIEW = "can_view"
    CAN_EDIT = "can_edit"
    CAN_MANAGE = "can_manage"


class GroupTypes:
    """
    A static utility class for defining permission groups for instances such 
    as `ExperimentSet`, `Experiment` and `ScoreSet`.
    """
    VIEWER = "viewers"
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
    from experiment.models import Experiment, ExperimentSet
    from scoreset.models import ScoreSet
    if not hasattr(instance, 'accession'):
        return False
    if not getattr(instance, 'accession'):
        return False
    if not isinstance(instance, Experiment) and \
            not isinstance(instance, ExperimentSet) and \
            not isinstance(instance, ScoreSet):
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
        return '{}-admins'.format(instance.accession)


def get_contributor_group_name_for_instance(instance):
    if valid_model_instance(instance):
        return '{}-contributors'.format(instance.accession)


def get_viewer_group_name_for_instance(instance):
    if valid_model_instance(instance):
        return '{}-viewers'.format(instance.accession)


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


def instances_for_user_with_group_permission(user, model, group_type):
    from experiment.models import Experiment, ExperimentSet
    from scoreset.models import ScoreSet

    if user_is_anonymous(user):
        return []

    if model == ExperimentSet:
        instances = ExperimentSet.objects.all()
    elif model == Experiment:
        instances = Experiment.objects.all()
    elif model == ScoreSet:
        instances = ScoreSet.objects.all()
    else:
        raise TypeError("Unrecognised model type {}.".format(model))

    group_type_callables = {
        GroupTypes.ADMIN: user_is_admin_for_instance,
        GroupTypes.CONTRIBUTOR: user_is_contributor_for_instance,
        GroupTypes.VIEWER: user_is_viewer_for_instance
    }
    is_in_group = group_type_callables.get(group_type, None)
    if is_in_group is None:
        raise ValueError("Unrecognised group type {}.".format(group_type))

    return [i for i in instances if is_in_group(user, i)]


# Group construction
# --------------------------------------------------------------------------- #
def make_admin_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_admin_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).exists():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.admin_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def make_contributor_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_contributor_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).exists():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.contributor_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def make_viewer_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_viewer_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).exists():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.viewer_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def make_all_groups_for_instance(instance):
    if valid_model_instance(instance):
        g1 = make_admin_group_for_instance(instance)
        g2 = make_contributor_group_for_instance(instance)
        g3 = make_viewer_group_for_instance(instance)
        return g1, g2, g3


# User assignment
# --------------------------------------------------------------------------- #
# Notes: A user should only be assigned to one group at any single time.
def assign_user_as_instance_admin(user, instance):
    if user_is_anonymous(user):
        return False
    try:
        group_name = get_admin_group_name_for_instance(instance)
        admin_group = Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        make_admin_group_for_instance(instance)

    admin_group = Group.objects.get(name=group_name)
    remove_user_as_instance_contributor(user, instance)
    remove_user_as_instance_viewer(user, instance)
    user.groups.add(admin_group)
    user.save()
    return True


def assign_user_as_instance_contributor(user, instance):
    if user_is_anonymous(user):
        return False
    try:
        group_name = get_contributor_group_name_for_instance(instance)
        contrib_group = Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        make_contributor_group_for_instance(instance)

    contrib_group = Group.objects.get(name=group_name)
    remove_user_as_instance_admin(user, instance)
    remove_user_as_instance_viewer(user, instance)
    user.groups.add(contrib_group)
    user.save()
    return True


def assign_user_as_instance_viewer(user, instance):
    if user_is_anonymous(user):
        return False
    try:
        group_name = get_viewer_group_name_for_instance(instance)
        viewer_group = Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        make_viewer_group_for_instance(instance)

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
        contrib_group = Group.objects.get(name=group_name)
        user.groups.remove(contrib_group)
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
