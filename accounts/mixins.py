from django.contrib.auth.models import User, Group
from django.db.models import QuerySet

from .permissions import (
    GroupTypes,
    assign_user_as_instance_viewer,
    assign_user_as_instance_admin,
    assign_user_as_instance_editor,
    remove_user_as_instance_admin,
    remove_user_as_instance_editor,
    remove_user_as_instance_viewer,
    get_admin_group_name_for_instance,
    get_editor_group_name_for_instance,
    get_viewer_group_name_for_instance,
)


def filter_anon(qs):
    """filter anon users from a query."""
    return qs.exclude(username__iexact="AnonymousUser")


def _add_users(instance, users, group):
    if group == GroupTypes.ADMIN:
        func = assign_user_as_instance_admin
    elif group == GroupTypes.EDITOR:
        func = assign_user_as_instance_editor
    elif group == GroupTypes.VIEWER:
        func = assign_user_as_instance_viewer
    else:
        raise ValueError("Unrecognised permission group {}.".format(group))
    if isinstance(users, (list, set, tuple, QuerySet)):
        all_assigned = True
        for u in users:
            all_assigned &= func(user=u, instance=instance)
        return all_assigned
    elif isinstance(users, User):
        return func(user=users, instance=instance)
    else:
        raise TypeError("Expected iterable or User. Found {}.".format(
            type(users).__name__))


def _remove_users(instance, users, group):
    if group == GroupTypes.ADMIN:
        func = remove_user_as_instance_admin
    elif group == GroupTypes.EDITOR:
        func = remove_user_as_instance_editor
    elif group == GroupTypes.VIEWER:
        func = remove_user_as_instance_viewer
    else:
        raise ValueError("Unrecognised permission group {}.".format(group))
    if isinstance(users, (list, set, tuple, QuerySet)):
        all_removed = True
        for u in users:
            all_removed &= func(user=u, instance=instance)
        return all_removed
    elif isinstance(users, User):
        return func(user=users, instance=instance)
    else:
        raise TypeError("Expected iterable or User. Found {}.".format(
            type(users).__name__))


class GroupPermissionMixin(object):
    """
    Mixin to provide functionality to a :class:dataset.`DatasetModel` that
    allows access to the users assigned to each group for a particular
    instance.
    """
    @property
    def admin_group_name(self):
        return get_admin_group_name_for_instance(self)

    @property
    def editor_group_name(self):
        return get_editor_group_name_for_instance(self)

    @property
    def viewer_group_name(self):
        return get_viewer_group_name_for_instance(self)

    @property
    def administrators(self):
        """
        Returns a :class:`QuerySet` of administrators for an instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that have 'edit', 'view' and
            'manage' permissions.
        """
        groups = Group.objects.filter(name=self.admin_group_name)
        if not groups.count():
            return User.objects.none()
        return groups.first().user_set.all()

    @property
    def editors(self):
        """
        Returns a :class:`QuerySet` of users than can edit this instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that have 'edit' permissions.
        """
        groups = Group.objects.filter(name=self.editor_group_name)
        if not groups.count():
            return User.objects.none()
        return groups.first().user_set.all()

    @property
    def viewers(self):
        """
        Returns a :class:`QuerySet` of viewers for an instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that only have the 'view' permission.
        """
        groups = Group.objects.filter(name=self.viewer_group_name)
        if not groups.count():
            return User.objects.none()
        return groups.first().user_set.all()

    @property
    def contributors(self):
        """
        Returns a :class:`QuerySet` of contributors for an instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that have both 'edit' and
            'view' permissions.
        """
        return (self.administrators | self.editors | self.viewers).distinct()

    def add_administrators(self, users):
        """
        Assigns user(s) as an administrator, removing them from any previous
        group assignment.
        """
        return _add_users(self, users, group=GroupTypes.ADMIN)

    def remove_administrators(self, users):
        """
        Removes user(s) as an administrator.
        """
        return _remove_users(self, users, group=GroupTypes.ADMIN)

    def add_editors(self, users):
        """
        Assigns user(s) as an editor, removing them from any previous
        group assignment.
        """
        return _add_users(self, users, group=GroupTypes.EDITOR)

    def remove_editors(self, users):
        """
        Removes user(s) as an editor.
        """
        return _remove_users(self, users, group=GroupTypes.EDITOR)

    def add_viewers(self, users):
        """
        Assigns user(s) as a viewer, removing them from any previous
        group assignment.
        """
        return _add_users(self, users, group=GroupTypes.VIEWER)

    def remove_viewers(self, users):
        """
        Removes user(s) as a viewer.
        """
        return _remove_users(self, users, group=GroupTypes.VIEWER)
