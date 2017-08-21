
from django.contrib.auth.models import Group, User
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from experiment.models import ExperimentSet, Experiment
from scoreset.models import ScoreSet

from .permissions import (
    GroupTypes,
    user_is_anonymous,
    instances_for_user_with_group_permission
)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    @classmethod
    def non_anonymous_profiles(cls):
        return [p for p in cls.objects.all() if not p.is_anon()]

    def is_anon(self):
        return user_is_anonymous(self.user)

    def __str__(self):
        return "{}_profile".format(self.user.username)

    def experimentsets(self):
        return self.administrator_experimentsets() + \
            self.contributor_experimentsets() + \
            self.viewer_experimentsets()

    def experiments(self):
        return self.administrator_experiments() + \
            self.contributor_experiments() + \
            self.viewer_experiments()

    def scoresets(self):
        return self.administrator_scoresets() + \
            self.contributor_scoresets() + \
            self.viewer_scoresets()

    def administrator_instances(self):
        return self.administrator_experimentsets() + \
            self.administrator_experiments() + \
            self.administrator_scoresets()

    def contributor_instances(self):
        return self.contributor_experimentsets() + \
            self.contributor_experiments() + \
            self.contributor_scoresets()

    def viewer_instances(self):
        return self.viewer_experimentsets() + \
            self.viewer_experiments() + \
            self.viewer_scoresets()

    # ExperimentSet access
    # ---------------------------------------------------------------------- #
    def administrator_experimentsets(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )

    def contributor_experimentsets(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.CONTRIBUTOR
        )

    def viewer_experimentsets(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.VIEWER
        )

    # Experiment access
    # ---------------------------------------------------------------------- #
    def administrator_experiments(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.ADMIN
        )

    def contributor_experiments(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.CONTRIBUTOR
        )

    def viewer_experiments(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.VIEWER
        )

    # ScoreSet access
    # ---------------------------------------------------------------------- #
    def administrator_scoresets(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.ADMIN
        )

    def contributor_scoresets(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.CONTRIBUTOR
        )

    def viewer_scoresets(self):
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.VIEWER
        )


# Post Save signals
# -------------------------------------------------------------------------- #
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
