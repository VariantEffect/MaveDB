
from django.contrib.auth.models import User

from .permissions import (
    GroupTypes,
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance,
)


class GroupPermissionMixin(object):

    def administrators(self):
        users = User.objects.all()
        admins = [u.pk for u in users if user_is_admin_for_instance(u, self)]
        return User.objects.filter(pk__in=admins)

    def contributors(self):
        users = User.objects.all()
        contrib = [
            u.pk for u in users
            if user_is_contributor_for_instance(u, self)
        ]
        return User.objects.filter(pk__in=contrib).exclude(is_superuser=True)

    def viewers(self):
        users = User.objects.all()
        viewers = [u.pk for u in users if user_is_viewer_for_instance(u, self)]
        return User.objects.filter(pk__in=viewers).exclude(is_superuser=True)
