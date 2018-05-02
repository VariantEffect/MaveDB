import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.factories import UserFactory
from accounts.permissions import assign_user_as_instance_admin

from dataset.models.scoreset import Experiment
from dataset.factories import ExperimentWithScoresetFactory


User = get_user_model()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('clear', nargs='?', type=bool, default=False)

    def handle(self, *args, **kwargs):
        password = "1234qwer"
        with transaction.atomic():
            for username in ['usera', 'userb', 'userb', 'userd']:
                user = UserFactory(username=username)
                user.set_password(password)
                user.save()
                instance = ExperimentWithScoresetFactory(private=False)
                for i in instance.children.all():
                    parent = i
                    while parent:
                        parent.private = False
                        parent.set_modified_by(user)
                        parent.set_created_by(user)
                        parent.save()
                        assign_user_as_instance_admin(user, instance)
                        parent = parent.parent

                sys.stdout.write("Created {}\n".format(instance.urn))
