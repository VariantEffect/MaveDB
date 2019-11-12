import sys
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from dataset import constants
from urn.models import get_model_by_urn

User = get_user_model()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--user", type=str, help="User ORCID")
        parser.add_argument("--urn", type=str, help="Dataset URN")
        parser.add_argument("--role", type=str, help="User role")

    def handle(self, *args, **kwargs):
        role = kwargs.get("role", None)
        valid_states = (
            constants.administrator,
            constants.editor,
            constants.viewer,
        )
        if role not in valid_states:
            raise ValueError(
                "Valid states are {}.".format(
                    "{} or {}".format(
                        ", ".join(valid_states[:-1]), valid_states[-1]
                    )
                )
            )

        urn = kwargs.get("urn", None)
        if not urn:
            raise ValueError("A valid URN is required.")

        user = kwargs.get("user", None)
        if not user:
            raise ValueError("A valid user is required.")

        instance = get_model_by_urn(urn)
        user_model = User.objects.get(username=user)
        if role == constants.administrator:
            instance.add_administrators(user_model)
        elif role == constants.editor:
            instance.add_editors(user_model)
        elif role == constants.viewer:
            instance.add_viewers(user_model)
        else:
            raise ValueError("Invalid user role.")
        instance.save()
        sys.stdout.write(
            "Added {} to {} with role {}.\n".format(user, instance, role)
        )
