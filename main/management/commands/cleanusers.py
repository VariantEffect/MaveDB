import sys
import idutils
from django.core.management.base import BaseCommand

from accounts.models import User

EXEMPT = ["AnonymousUser", "fowler-mavedb"]


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--exclude",
            type=str,
            help="Exclude these usernames from being deleted (comma separated).",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Dry run without deleting users.",
        )

    def handle(self, *args, **kwargs):
        dry_run = not kwargs.get("commit", False)
        if dry_run:
            sys.stdout.write("Running in dry mode\n")

        exclude = set(
            EXEMPT
            + [
                i
                for i in (kwargs.get("exclude", "") or "").split(",")
                if i.strip()
            ]
        )
        sys.stdout.write(f"Excluding names in {exclude}\n\n")
        for user in User.objects.all():
            delete = (not idutils.is_orcid(user.username)) and (
                not user.username in exclude
            )
            if delete:
                message = (
                    f"'{user.username}' is not an ORCID compliant username"
                )
                if not dry_run:
                    sys.stdout.write(f"{message}. Deleting user\n")
                    user.delete()
                else:
                    sys.stdout.write(f"{message}\n")

        if dry_run:
            sys.stdout.write(f"\nRun with --commit to delete these users\n")
