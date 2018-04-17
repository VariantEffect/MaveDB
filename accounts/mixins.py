from django.contrib.auth.models import User
from django.db.models import QuerySet

from .permissions import (
    user_is_anonymous,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_editor_for_instance,
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
            if user_editor_for_instance(u, self)
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
