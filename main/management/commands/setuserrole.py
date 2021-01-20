from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from manager.models import Role

User = get_user_model()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user", type=str, help="User ORCID")
        parser.add_argument("--role", type=str, help="User role")

    def handle(self, *args, **kwargs):
        role = kwargs.get("role", None)
        valid_roles = {r[0] for r in Role.choices()}
        if not role or role.upper() not in valid_roles:
            raise ValueError(
                f"Valid roles are {valid_roles}."
            )
        role = role.upper()

        user_id = kwargs.get("user", None)
        if not user_id:
            raise ValueError("A valid user is required.")

        try:
            user = User.objects.get(username=user_id)
        except user.DoesNotExist as e:
            raise ValueError(f"User with id {user_id} does not exist.")

        user.userrole.role = Role(role)
        user.save()
