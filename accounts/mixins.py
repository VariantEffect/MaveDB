
from django.contrib.auth.models import User

from .permissions import (
    user_is_admin_for_instance,
    user_is_contributor_for_instance,
    user_is_viewer_for_instance,
    contributors_for_instance
)


class GroupPermissionMixin(object):

    def administrators(self):
        users = User.objects.all()
        admins = [u.pk for u in users if user_is_admin_for_instance(u, self)]
        return User.objects.filter(pk__in=admins)

    def authors(self):
        users = User.objects.all()
        authors = [
            u.pk for u in users
            if user_is_contributor_for_instance(u, self)
        ]
        return User.objects.filter(pk__in=authors).exclude(is_superuser=True)

    def viewers(self):
        users = User.objects.all()
        viewers = [u.pk for u in users if user_is_viewer_for_instance(u, self)]
        return User.objects.filter(pk__in=viewers).exclude(is_superuser=True)

    def get_contributor_models(self):
        return list(contributors_for_instance(self))

    def get_contributors(self, string=True):
        authors = [
            u.profile.get_short_name()
            for u in contributors_for_instance(self)
        ]
        return ', '.join(authors) if string else authors

    def get_contributors_by_full_name(self, string=True):
        authors = [
            u.profile.get_full_name()
            for u in contributors_for_instance(self)
        ]
        return ', '.join(authors) if string else authors

    def get_contributors_by_username(self, string=True):
        authors = [u.username for u in contributors_for_instance(self)]
        return ', '.join(authors) if string else authors
