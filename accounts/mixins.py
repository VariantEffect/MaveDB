from django.contrib.auth.models import User
from django.db.models import QuerySet

from search.mixins import SearchMixin
from .permissions import (
    user_is_anonymous,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_editor_for_instance,
    user_is_viewer_for_instance,
)


def filter_su(qs):
    """filter superusers from a query."""
    if isinstance(qs, (list, set)):
        return [u for u in qs if not u.is_superuser]
    return qs.exclude(is_superuser=True)


def filter_anon(qs):
    """filter anon users from a query."""
    if isinstance(qs, (list, set)):
        return [u for u in qs if not user_is_anonymous(u)]
    else:
        users = [u.pk for u in qs if not user_is_anonymous(u)]
        return User.objects.filter(pk__in=users)


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


class UserSearchMixin(SearchMixin):
    """
    Filter :class:`User` instances by common fields:
        'username': 'username',
        'first_name': 'first_name',
        'last_name': 'last_name',
    """
    @staticmethod
    def search_field_to_model_field():
        return {
            'username': 'username',
            'first_name': 'first_name',
            'last_name': 'last_name',
        }

    def search_field_to_function(self):
        return {
            'username': self.filter_username,
            'first_name': self.filter_first_name,
            'last_name': self.filter_last_name,
        }

    def filter_username(self, value):
        return self.search_to_q(
            value, field_name='username', filter_type='iexact')

    def filter_first_name(self, value):
        return self.search_to_q(
            value, field_name='first_name', filter_type='icontains')

    def filter_last_name(self, value):
        return self.search_to_q(
            value, field_name='last_name', filter_type='icontains')
