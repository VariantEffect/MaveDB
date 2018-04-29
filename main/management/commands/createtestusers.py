from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.factories import UserFactory

User = get_user_model()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('clear', nargs='?', type=bool, default=False)

    def handle(self, *args, **kwargs):
        if kwargs.get('clear', False):
            if not settings.DEBUG:
                raise ValueError("Cannot clear user table when DEBUG is True")
            else:
                User.objects.all().delete()

        with transaction.atomic():
            password = "1234qwer"
            usera = UserFactory(username="usera")
            userb = UserFactory(username="userb")
            userc = UserFactory(username="userc")

            usera.set_password(password)
            usera.save()

            userb.set_password(password)
            userb.save()

            userc.set_password(password)
            userc.save()
