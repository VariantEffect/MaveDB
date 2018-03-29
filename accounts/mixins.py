
from django.contrib.auth.models import User
from django.db.models import QuerySet

from .permissions import (
    user_is_anonymous,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
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
    def _format_as(self, group, string, format_=None):
        """
        Format the users assigned to `group` by using their full name or
        username.

        Parameters
        ----------
        group : str, choices are {'administrators', 'contributors', 'viewers'}
            The string attribute of the function to call.

        string : bool
            If True, will comma separate users for 'group'

        format_ : str, choices: {'short', 'username', None, 'full'} . Default: None
            How the users should be formatted.

        Returns
        -------
        `list`
            A list of users by username or full name.
        """
        users = getattr(self, group)()
        if format_ == "username":
            users = [u.username for u in users]
        elif format_ == "full":
            users = [u.get_full_name() for u in users]
        elif format_ == "short":
            users = [u.get_short_name() for u in users]
        return ', '.join(users) if string else users

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
            if user_is_contributor_for_instance(u, self) or \
            user_is_admin_for_instance(u, self)
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

    def format_using_full_name(self, group, string=False):
        """
        Returns users in permission group `group` for this instnace.
        """
        return self._format_as(group, string=string, format_='full')

    def format_using_short_name(self, group, string=False):
        """
        Returns users in permission group `group` for this instnace.
        """
        return self._format_as(group, string=string, format_='short')

    def format_using_username(self, group, string=False):
        """
        Returns users in permission group `group` for this instnace.
        """
        return self._format_as(group, string=string, format_='username')

