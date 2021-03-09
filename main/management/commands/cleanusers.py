import sys
import idutils
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for user in User.objects.all():
            if not idutils.is_orcid(user.username):
                sys.stdout.write(
                    f"'{user.username}' is not an ORCID compliant username, "
                    f"deleting user.\n"
                )
                user.delete()
