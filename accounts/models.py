from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.html import format_html

from dataset.models.experimentset import ExperimentSet
from dataset.models.experiment import Experiment
from dataset.models.scoreset import ScoreSet

from .permissions import (
    GroupTypes,
    user_is_anonymous,
    instances_for_user_with_group_permission
)


class Profile(models.Model):
    """
    A Profile is associated with a user. It contains helper functions
    which can be used to format the users details like orcid url, name, and
    contains utility functions for obtaining :class:`DatasetModel` instances
    that are associated with the user.

    Attributes
    ----------
    user : :class:`models.OnOneToOneField`
        The foreign key relationship associating a profile with a user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    @classmethod
    def non_anonymous_profiles(cls):
        """Returns a list of all non-anonymous profiles."""
        return [p for p in cls.objects.all() if not p.is_anon()]

    def is_anon(self):
        """
        Checks if the user associated with this profile is anonymous.

        Returns
        -------
        `bool`
            True if the profile and user are anonymous.
        """
        return user_is_anonymous(self.user)
    
    def get_orcid_url(self):
        """
        Returns the ORCID url for the owner of this profile, which is
        based off the username parsed from the ORCID OAuth.

        Returns
        -------
        `str` or `None`
            The ORCID url for this user, otherwise None if the user is
            anonymous.
        """
        if self.is_anon():
            return None
        else:
            return 'https://orcid.org/{}'.format(self.user.username)
    
    def get_full_name_hyperlink(self):
        """
        Returns the full name formatted as a hyperlink tag referencing the
        ORCID url.

        Returns
        -------
        `str`
            Returns 'anonymous user' if the user is anon, otherwise a
            <a/> tag with the user's full name as the inner HTML.
        """
        if self.is_anon():
            return 'anonymous user'
        else:
            return format_html('<a href="{url}">{name}</a>'.format(
                url=self.get_orcid_url(),
                name=self.get_full_name()))

    def get_full_name(self):
        """
        Returns the users full name formatted as "<first>, <last>" If the user
        does not have a last name, the first name is returned. If the user has
        neither, then the username is returned.

        Returns
        -------
        `str`
            Full, first or username as a string. Returns None if the user is
            anon.
        """
        if self.is_anon():
            return None
        if not self.user.last_name:
            if not self.user.first_name:
                return self.user.username
            else:
                # support for mononyms
                return self.user.first_name.capitalize()
        else:
            return '{} {}'.format(
                self.user.first_name.capitalize(),
                self.user.last_name.capitalize()
            )

    def get_short_name(self):
        """
        Returns the users short name formatted as
        "<last name>, <first name initial>". If the user does not have a last
        name, the first name is returned. If the user has
        neither, then the username is returned.

        Returns
        -------
        `str`
            Short name, first or username as a string. Returns None if the user
            is anon.
        """
        if self.is_anon():
            return None
        if not self.user.last_name:
            if not self.user.first_name:
                return self.user.username
            else:
                # support for mononyms
                return self.user.first_name.capitalize()
        else:
            return '{}, {}'.format(
                self.user.last_name.capitalize(),
                self.user.first_name[0].capitalize()
            )

    def __str__(self):
        return "{}_profile".format(self.user.username)

    def experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user is assoicated
        with.
        """
        return self.administrator_experimentsets() + \
            self.contributor_experimentsets() + \
            self.viewer_experimentsets()

    def experiments(self):
        """
        Return a list of :class:`Experiment` instances the user is assoicated
        with.
        """
        return self.administrator_experiments() + \
            self.contributor_experiments() + \
            self.viewer_experiments()

    def scoresets(self):
        """
        Return a list of :class:`ScoreSet` instances the user is assoicated
        with.
        """
        return self.administrator_scoresets() + \
            self.contributor_scoresets() + \
            self.viewer_scoresets()

    def administrator_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is an admin
        for.
        """
        return self.administrator_experimentsets() + \
            self.administrator_experiments() + \
            self.administrator_scoresets()

    def contributor_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is a
        contributor for.
        """
        return self.contributor_experimentsets() + \
            self.contributor_experiments() + \
            self.contributor_scoresets()

    def viewer_instances(self):
        """
        Return a list of :class:`DatasetModel` instances the user is a viewer
        for.
        """
        return self.viewer_experimentsets() + \
            self.viewer_experiments() + \
            self.viewer_scoresets()

    # ExperimentSet access
    # ---------------------------------------------------------------------- #
    def administrator_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        administrates.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.ADMIN
        )

    def contributor_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        contributes to.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.CONTRIBUTOR
        )

    def viewer_experimentsets(self):
        """
        Return a list of :class:`ExperimentSet` instances the user
        can only view.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ExperimentSet,
            group_type=GroupTypes.VIEWER
        )

    # Experiment access
    # ---------------------------------------------------------------------- #
    def administrator_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        administrates.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.ADMIN
        )

    def contributor_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        contributes to.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.CONTRIBUTOR
        )

    def viewer_experiments(self):
        """
        Return a list of :class:`Experiment` instances the user
        can only view.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=Experiment,
            group_type=GroupTypes.VIEWER
        )

    # ScoreSet access
    # ---------------------------------------------------------------------- #
    def administrator_scoresets(self):
        """
        Return a list of :class:`Experiment` instances the user
        administrates.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.ADMIN
        )

    def contributor_scoresets(self):
        """
        Return a list of :class:`ScoreSet` instances the user
        contributes to.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.CONTRIBUTOR
        )

    def viewer_scoresets(self):
        """
        Return a list of :class:`ScoreSet` instances the user
        can only view.
        """
        return instances_for_user_with_group_permission(
            user=self.user,
            model=ScoreSet,
            group_type=GroupTypes.VIEWER
        )


# Post Save signals
# -------------------------------------------------------------------------- #
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Post-save signal invoked when a new user is saved/created. Creates a
    new profile for the user if this a first time call.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Saves profile whenever associated user is saved.
    """
    instance.profile.save()
