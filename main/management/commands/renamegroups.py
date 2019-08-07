import sys

from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group

from accounts.permissions import GroupTypes
from dataset import models


class Command(BaseCommand):
    @staticmethod
    def rename_groups(instance):
        for group_type in GroupTypes():
            name = "{}-{}".format(instance.urn, group_type)
            group = Group.objects.get(name=name)
            group.name = "{}:{}-{}".format(
                instance.class_name(), instance.pk, group_type
            )
            group.save()
            sys.stdout.write("Renamed '{}' to '{}'\n".format(name, group.name))

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            for scoreset in models.experimentset.ExperimentSet.objects.all():
                self.rename_groups(scoreset)

            for scoreset in models.experiment.Experiment.objects.all():
                self.rename_groups(scoreset)

            for scoreset in models.scoreset.ScoreSet.objects.all():
                self.rename_groups(scoreset)
