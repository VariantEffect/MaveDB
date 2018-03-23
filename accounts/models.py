
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.html import format_html

from dataset.models import ExperimentSet, Experiment, ScoreSet

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
    
    def get_orcid_url(self):
        if self.is_anon():
            return None
        else:
            return 'https://orcid.org/{}'.format(self.user.username)
    
    def get_full_name_hyperlink(self):
        if self.is_anon():
            return 'anonymous user'
        else:
            return format_html('<a href="{url}">{name}</a>'.format(
                url=self.get_orcid_url(),
                name=self.get_full_name()))

    def get_full_name(self):
        if self.is_anon():
            return None
        if not self.user.last_name:
            if not self.user.first_name:
                return self.user.username
            else:
                # support for mononyms
                return self.user.first_name
        else:
            return '{} {}'.format(
                self.user.first_name,
                self.user.last_name
            )

    def get_short_name(self):
        if self.is_anon():
            return None
        if not self.user.last_name:
            if not self.user.first_name:
                return self.user.username
            else:
                # support for mononyms
                return self.user.first_name
        else:
            return '{}, {}'.format(
                self.user.last_name,
                self.user.first_name[0]
            )

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
