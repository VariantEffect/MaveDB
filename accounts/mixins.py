from django.contrib.auth.models import User
from django.db.models import QuerySet

from .permissions import (
    GroupTypes,
    user_is_anonymous,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_editor_for_instance,
    user_is_viewer_for_instance,
    assign_user_as_instance_viewer,
    assign_user_as_instance_admin,
    assign_user_as_instance_editor,
    remove_user_as_instance_admin,
    remove_user_as_instance_editor,
    remove_user_as_instance_viewer,
)


def filter_anon(qs):
    """filter anon users from a query."""
    if isinstance(qs, (list, set)):
        return [u for u in qs if not user_is_anonymous(u)]
    else:
        users = [u.pk for u in qs if not user_is_anonymous(u)]
        return User.objects.filter(pk__in=users)


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
    def administrators(self):
        """
        Returns a :class:`QuerySet` of administrators for an instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that have 'edit', 'view' and
            'manage' permissions.
        """
        users = User.objects.all()
        admins = [u.pk for u in users if user_is_admin_for_instance(u, self)]
        return filter_anon(User.objects.filter(pk__in=admins))

    def contributors(self):
        """
        Returns a :class:`QuerySet` of contributors for an instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that have both 'edit' and
            'view' permissions.
        """
        contributors = [
            u.pk for u in User.objects.all()
            if user_is_contributor_for_instance(u, self)
        ]
        return filter_anon(User.objects.filter(pk__in=contributors))

    def editors(self):
        """
        Returns a :class:`QuerySet` of users than can edit this instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that have 'edit' permissions.
        """
        editors = [
            u.pk for u in User.objects.all()
            if user_is_editor_for_instance(u, self)
        ]
        return filter_anon(User.objects.filter(pk__in=editors))

    def viewers(self):
        """
        Returns a :class:`QuerySet` of viewers for an instance.

        Returns
        -------
        :class:`QuerySet`
            A query set instance of users that only have the 'view' permission.
        """
        users = User.objects.all()
        viewers = [u.pk for u in users if user_is_viewer_for_instance(u, self)]
        return filter_anon(User.objects.filter(pk__in=viewers))

    def users_with_manage_permission(self):
        """
        Returns all users with `dataset.can_manage` permission for
        this instance.
        """
        return self.administrators()

    def users_with_edit_permission(self):
        """
        Returns all users with `dataset.can_edit` permission for this instance.
        """
        return self.editors().union(self.administrators())

    def users_with_view_permission(self):
        """
        Returns all users with `dataset.can_view` permission for this instance.
        """
        return self.administrators().union(
            self.editors()).union(self.viewers())

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
