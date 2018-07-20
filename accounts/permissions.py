from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

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
    ADMIN = "administrator"
    EDITOR = "editor"
    VIEWER = "viewer"
    
    def __iter__(self):
        return iter([self.ADMIN, self.EDITOR, self.VIEWER])

    @staticmethod
    def admin_permissions():
        return [
            PermissionTypes.CAN_VIEW,
            PermissionTypes.CAN_EDIT,
            PermissionTypes.CAN_MANAGE,
        ]

    @staticmethod
    def editor_permissions():
        return [
            PermissionTypes.CAN_EDIT,
            PermissionTypes.CAN_VIEW,
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
        GroupTypes.ADMIN, GroupTypes.EDITOR, GroupTypes.VIEWER
    }


def user_is_anonymous(user):
    if not hasattr(user, 'username'):
        return
    return isinstance(user, AnonymousUser) or \
        user.username == ANONYMOUS_USER_NAME


def get_admin_group_name_for_instance(instance):
    if valid_model_instance(instance):
        klass = instance.__class__.__name__.lower()
        return '{}:{}-{}'.format(klass, instance.pk, GroupTypes.ADMIN)


def get_editor_group_name_for_instance(instance):
    if valid_model_instance(instance):
        klass = instance.__class__.__name__.lower()
        return '{}:{}-{}'.format(klass, instance.pk, GroupTypes.EDITOR)


def get_viewer_group_name_for_instance(instance):
    if valid_model_instance(instance):
        klass = instance.__class__.__name__.lower()
        return '{}:{}-{}'.format(klass, instance.pk, GroupTypes.VIEWER)


def user_is_admin_for_instance(user, instance):
    group_name = get_admin_group_name_for_instance(instance)
    if group_name is not None:
        return group_name in set([g.name for g in user.groups.all()])
    else:
        return False


def user_is_editor_for_instance(user, instance):
    group_name = get_editor_group_name_for_instance(instance)
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


def user_is_contributor_for_instance(user, instance):
    return user_is_admin_for_instance(user, instance) or \
           user_is_editor_for_instance(user, instance) or \
           user_is_viewer_for_instance(user, instance)


GROUP_TYPE_CALLBACK = {
    GroupTypes.ADMIN: user_is_admin_for_instance,
    GroupTypes.EDITOR: user_is_editor_for_instance,
    GroupTypes.VIEWER: user_is_viewer_for_instance,
}


def instances_for_user_with_group_permission(user, model, group_type):
    """
    Return all instances that the user is in `group_type` for.

    Parameters
    ----------
    user : `User`
        The user to retrieve instances for.
    model : `class`
        The instance model class.
    group_type : `str`
        The group, which is either admins, editors or viewers.

    Returns
    -------
    `QuerySet`
    """
    from dataset.models.experimentset import ExperimentSet
    from dataset.models.experiment import Experiment
    from dataset.models.scoreset import ScoreSet

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

    is_in_group = GROUP_TYPE_CALLBACK.get(group_type, None)
    if is_in_group is None:
        raise ValueError("Unrecognised group type {}.".format(group_type))

    pks = set([i.pk for i in instances if is_in_group(user, i)])
    return model.objects.filter(pk__in=pks).all()


def contributors_for_instance(instance):
    author_pks = set()
    if not valid_model_instance(instance):
        raise TypeError("Invalid type supplied {}".format(type(instance)))
    users = User.objects.all()
    for u in users:
        if user_is_contributor_for_instance(u, instance):
            author_pks.add(u.pk)
    return User.objects.filter(pk__in=author_pks)


# Group construction
# --------------------------------------------------------------------------- #
def create_admin_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_admin_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).count():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.admin_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def create_editor_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_editor_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).count():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.editor_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def create_viewer_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_viewer_group_name_for_instance(instance)
        if not Group.objects.filter(name=name).count():
            group = Group.objects.create(name=name)
            for permission in GroupTypes.viewer_permissions():
                assign_perm(permission, group, instance)
            return group
        return Group.objects.get(name=name)


def create_all_groups_for_instance(instance):
    if valid_model_instance(instance):
        g1 = create_admin_group_for_instance(instance)
        g2 = create_editor_group_for_instance(instance)
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


def delete_editor_group_for_instance(instance):
    if valid_model_instance(instance):
        name = get_editor_group_name_for_instance(instance)
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
        author_name = delete_editor_group_for_instance(instance)
        viewer_name = delete_viewer_group_for_instance(instance)
        return admin_name, author_name, viewer_name


# User assignment
# --------------------------------------------------------------------------- #
# Notes: A user should only be assigned to one group at any single time.
def assign_user_as_instance_admin(user, instance):
    if user_is_anonymous(user):
        return False
    if not isinstance(user, User):
        raise TypeError(
            "Expected type User, found {}.".format(type(user).__name__))

    group_name = get_admin_group_name_for_instance(instance)
    try:
        Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        create_admin_group_for_instance(instance)

    admin_group, _ = Group.objects.get_or_create(name=group_name)
    remove_user_as_instance_editor(user, instance)
    remove_user_as_instance_viewer(user, instance)
    user.groups.add(admin_group)
    user.save()
    return True


def assign_user_as_instance_editor(user, instance):
    if user_is_anonymous(user):
        return False
    if not isinstance(user, User):
        raise TypeError(
            "Expected type User, found {}.".format(type(user).__name__))

    group_name = get_editor_group_name_for_instance(instance)
    try:
        Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        create_editor_group_for_instance(instance)

    author_group = Group.objects.get(name=group_name)
    remove_user_as_instance_admin(user, instance)
    remove_user_as_instance_viewer(user, instance)
    user.groups.add(author_group)
    user.save()
    return True


def assign_user_as_instance_viewer(user, instance):
    if user_is_anonymous(user):
        return False
    if not isinstance(user, User):
        raise TypeError(
            "Expected type User, found {}.".format(type(user).__name__))

    group_name = get_viewer_group_name_for_instance(instance)
    try:
        Group.objects.get(name=group_name)
    except ObjectDoesNotExist:
        create_viewer_group_for_instance(instance)

    viewer_group = Group.objects.get(name=group_name)
    remove_user_as_instance_admin(user, instance)
    remove_user_as_instance_editor(user, instance)
    user.groups.add(viewer_group)
    user.save()
    return True


# User removal
# --------------------------------------------------------------------------- #
def remove_user_as_instance_admin(user, instance):
    if not isinstance(user, User):
        raise TypeError(
            "Expected type User, found {}.".format(type(user).__name__))
    try:
        group_name = get_admin_group_name_for_instance(instance)
        admin_group = Group.objects.get(name=group_name)
        user.groups.remove(admin_group)
        user.save()
        return True
    except ObjectDoesNotExist:
        return False


def remove_user_as_instance_editor(user, instance):
    if not isinstance(user, User):
        raise TypeError(
            "Expected type User, found {}.".format(type(user).__name__))
    try:
        group_name = get_editor_group_name_for_instance(instance)
        author_group = Group.objects.get(name=group_name)
        user.groups.remove(author_group)
        user.save()
        return True
    except ObjectDoesNotExist:
        return False


def remove_user_as_instance_viewer(user, instance):
    if not isinstance(user, User):
        raise TypeError(
            "Expected type User, found {}.".format(type(user).__name__))
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
    for user in instance.administrators():
        if user not in users:
            remove_user_as_instance_admin(user, instance)
    for user in users:
        if user not in instance.administrators():
            assign_user_as_instance_admin(user, instance)


def update_editor_list_for_instance(users, instance):
    for user in instance.editors():
        if user not in users:
            remove_user_as_instance_editor(user, instance)
    for user in users:
        if user not in instance.editors():
            assign_user_as_instance_editor(user, instance)


def update_viewer_list_for_instance(users, instance):
    for user in instance.viewers():
        if user not in users:
            remove_user_as_instance_viewer(user, instance)
    for user in users:
        if user not in instance.viewers():
            assign_user_as_instance_viewer(user, instance)


def assign_superusers_as_admin(instance):
    sus = User.objects.filter(is_superuser=True)
    for su in sus:
        assign_user_as_instance_admin(su, instance)
        while instance.parent:
            instance = instance.parent
            assign_user_as_instance_admin(su, instance)
